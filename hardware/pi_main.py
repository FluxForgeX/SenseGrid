#!/usr/bin/env python
"""
SenseGrid Raspberry Pi Main Controller

Orchestrates all hardware services and connects to FastAPI backend.

Usage:
    python pi_main.py                    # Run all services
    python pi_main.py --no-camera        # Run without ESP32-CAM
    python pi_main.py --no-gpio          # Run without GPIO (Windows testing)
"""

import argparse
import signal
import sys
import time
import json
import requests
import socketio
from typing import Optional

from config import PiConfig, config
from sensor_bridge import SensorBridge, SensorData
from esp32cam_client import ESP32CamClient
from action_controller import ActionController


class SenseGridPiController:
    """
    Main controller that orchestrates:
    - Sensor data ingestion from Arduino
    - Camera frame capture from ESP32-CAM
    - Intruder detection via backend API
    - GPIO action control
    - Real-time Socket.IO communication
    """
    
    def __init__(self, config: PiConfig):
        self.config = config
        
        # Services
        self.sensor_bridge: Optional[SensorBridge] = None
        self.esp32cam: Optional[ESP32CamClient] = None
        self.action_controller: Optional[ActionController] = None
        
        # Socket.IO client
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=0)
        self._setup_socketio_events()
        
        # State
        self._running = False
        self._auth_token: Optional[str] = None
        self._last_alert_time: float = 0
        self._detection_count: int = 0
    
    def _setup_socketio_events(self):
        """Setup Socket.IO event handlers."""
        
        @self.sio.event
        def connect():
            print("[pi_main] ✅ Connected to backend Socket.IO")
            # Identify as a Pi device
            self.sio.emit("device_register", {
                "deviceId": self.config.backend.device_id,
                "roomId": self.config.backend.room_id,
                "type": "raspberry_pi"
            })
        
        @self.sio.event
        def disconnect():
            print("[pi_main] ⚠️ Disconnected from backend")
        
        @self.sio.on("action:command")
        def on_action_command(data):
            """Handle action commands from backend/GUI."""
            print(f"[pi_main] 📥 Action command: {data}")
            
            action = data.get("action")
            state = data.get("state", data.get("value"))
            
            if action and self.action_controller:
                if isinstance(state, str):
                    state = state.upper() == "ON"
                self.action_controller.set_state(action, state)
        
        @self.sio.on("action:update")
        def on_action_update(data):
            """Handle action updates (e.g., fan toggle from GUI)."""
            print(f"[pi_main] 📥 Action update: {data}")
            
            sensor = data.get("sensor")
            action = data.get("action")
            
            if sensor and action and self.action_controller:
                state = action.upper() == "ON"
                # Map sensor to actuator (e.g., temperature -> fan)
                actuator_map = {
                    "temperature": "fan",
                    "gas": "fan",
                    "flame": "buzzer",
                }
                actuator = actuator_map.get(sensor, sensor)
                self.action_controller.set_state(actuator, state)
    
    def _authenticate(self) -> bool:
        """Authenticate with backend and get JWT token."""
        try:
            response = requests.post(
                f"{self.config.backend.api_url}/auth/login",
                json={
                    "email": self.config.backend.email,
                    "password": self.config.backend.password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                self._auth_token = response.json().get("token")
                print(f"[pi_main] ✅ Authenticated as {self.config.backend.email}")
                return True
            else:
                print(f"[pi_main] ❌ Auth failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"[pi_main] ❌ Auth error: {e}")
            return False
    
    def _on_sensor_data(self, data: SensorData):
        """Handle new sensor data from Arduino."""
        # Forward to backend via Socket.IO
        if self.sio.connected:
            payload = {
                "deviceId": self.config.backend.device_id,
                "roomId": self.config.backend.room_id,
                "sensors": {
                    "temperature": data.temperature,
                    "humidity": data.humidity,
                    "gas": data.gas,
                    "flame": data.flame,
                    "distance": data.distance,
                },
                "timestamp": int(data.timestamp * 1000)
            }
            self.sio.emit("device_update", payload)
        
        # Check for auto-actions (e.g., high gas -> turn on fan)
        self._check_auto_actions(data)
    
    def _check_auto_actions(self, data: SensorData):
        """Trigger automatic actions based on sensor thresholds."""
        if not self.action_controller:
            return
        
        # Gas threshold -> Fan
        if data.gas > 350:
            if not self.action_controller.get_state("fan"):
                print(f"[pi_main] ⚠️ High gas ({data.gas}ppm) - turning on fan")
                self.action_controller.set_state("fan", True)
        
        # Flame detected -> Buzzer
        if data.flame == 1:
            print(f"[pi_main] 🔥 FLAME DETECTED - triggering alarm!")
            self.action_controller.trigger_alarm(duration=10.0)
        
        # Temperature threshold -> Fan
        if data.temperature > 35:
            if not self.action_controller.get_state("fan"):
                print(f"[pi_main] 🌡️ High temp ({data.temperature}°C) - turning on fan")
                self.action_controller.set_state("fan", True)
    
    def _on_camera_frame(self, frame_bytes: bytes, timestamp: float):
        """Handle new frame from ESP32-CAM."""
        # Check cooldown
        if time.time() - self._last_alert_time < self.config.detection.alert_cooldown:
            return
        
        # Send to detection API
        self._run_detection(frame_bytes)
    
    def _run_detection(self, frame_bytes: bytes):
        """Send frame to backend for intruder detection."""
        if not self._auth_token:
            return
        
        try:
            response = requests.post(
                f"{self.config.backend.api_url}/intruder/detect",
                headers={"Authorization": f"Bearer {self._auth_token}"},
                files={"file": ("frame.jpg", frame_bytes, "image/jpeg")},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("intruder_detected"):
                    self._handle_intruder_alert(result)
            else:
                print(f"[pi_main] ⚠️ Detection API error: {response.status_code}")
                
        except Exception as e:
            print(f"[pi_main] ❌ Detection error: {e}")
    
    def _handle_intruder_alert(self, detection_result: dict):
        """Handle intruder detection alert."""
        self._detection_count += 1
        self._last_alert_time = time.time()
        
        detections = detection_result.get("detections", [])
        alert_id = detection_result.get("alert_id")
        
        # Check if Human detected (not just Animal)
        humans = [d for d in detections if d.get("class") == "Human"]
        
        if humans:
            print(f"[pi_main] 🚨 INTRUDER ALERT! {len(humans)} human(s) detected, alert_id={alert_id}")
            
            # Trigger buzzer
            if self.config.detection.trigger_buzzer and self.action_controller:
                self.action_controller.trigger_alarm(
                    duration=self.config.detection.buzzer_duration
                )
        else:
            print(f"[pi_main] 📷 Detection: {[d.get('class') for d in detections]} (no humans)")
    
    def start(self):
        """Start all services."""
        print("=" * 60)
        print("SenseGrid Raspberry Pi Controller")
        print("=" * 60)
        
        # Authenticate
        if not self._authenticate():
            print("[pi_main] ⚠️ Running without authentication")
        
        # Connect to Socket.IO
        try:
            print(f"[pi_main] Connecting to {self.config.backend.socketio_url}...")
            self.sio.connect(self.config.backend.socketio_url)
        except Exception as e:
            print(f"[pi_main] ⚠️ Socket.IO connection failed: {e}")
        
        # Initialize action controller
        if self.config.enable_gpio:
            self.action_controller = ActionController(
                config=self.config.action_controller
            )
            self.action_controller.initialize()
        
        # Start sensor bridge
        if self.config.enable_sensors:
            self.sensor_bridge = SensorBridge(
                config=self.config.sensor_bridge,
                on_data=self._on_sensor_data
            )
            self.sensor_bridge.start()
        
        # Start ESP32-CAM client
        if self.config.enable_camera:
            self.esp32cam = ESP32CamClient(
                config=self.config.esp32cam,
                on_frame=self._on_camera_frame
            )
            self.esp32cam.start()
        
        self._running = True
        print("[pi_main] ✅ All services started")
        print("=" * 60)
    
    def stop(self):
        """Stop all services."""
        print("[pi_main] Stopping services...")
        self._running = False
        
        if self.sensor_bridge:
            self.sensor_bridge.stop()
        
        if self.esp32cam:
            self.esp32cam.stop()
        
        if self.action_controller:
            self.action_controller.cleanup()
        
        if self.sio.connected:
            self.sio.disconnect()
        
        print("[pi_main] ✅ All services stopped")
    
    def run_forever(self):
        """Run until interrupted."""
        self.start()
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[pi_main] Interrupted")
        finally:
            self.stop()


def parse_args():
    parser = argparse.ArgumentParser(description="SenseGrid Raspberry Pi Controller")
    parser.add_argument("--no-sensors", action="store_true", help="Disable sensor bridge")
    parser.add_argument("--no-camera", action="store_true", help="Disable ESP32-CAM")
    parser.add_argument("--no-gpio", action="store_true", help="Disable GPIO (for Windows testing)")
    parser.add_argument("--serial-port", type=str, help="Arduino serial port")
    parser.add_argument("--esp32-url", type=str, help="ESP32-CAM URL")
    parser.add_argument("--backend-url", type=str, help="Backend API URL")
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Override config from args
    if args.no_sensors:
        config.enable_sensors = False
    if args.no_camera:
        config.enable_camera = False
    if args.no_gpio:
        config.enable_gpio = False
    if args.serial_port:
        config.sensor_bridge.serial_port = args.serial_port
    if args.esp32_url:
        config.esp32cam.stream_url = args.esp32_url
    if args.backend_url:
        config.backend.api_url = args.backend_url
        config.backend.socketio_url = args.backend_url.replace("/api", "")
    
    # Setup signal handlers
    controller = SenseGridPiController(config)
    
    def signal_handler(sig, frame):
        print("\n[pi_main] Shutdown signal received")
        controller.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    controller.run_forever()


if __name__ == "__main__":
    main()
