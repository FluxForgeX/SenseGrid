"""
Hardware Configuration

All hardware-related settings. Modify this file for your specific setup.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SensorBridgeConfig:
    """Arduino Serial/Bluetooth connection settings."""
    # Serial port (Linux: /dev/ttyUSB0, /dev/ttyACM0, /dev/rfcomm0 for Bluetooth)
    # Windows: COM3, COM4, etc.
    serial_port: str = os.getenv("ARDUINO_SERIAL_PORT", "/dev/ttyUSB0")
    baud_rate: int = int(os.getenv("ARDUINO_BAUD_RATE", "9600"))
    timeout: float = 2.0
    
    # Expected sensor keys from Arduino JSON
    sensor_keys: List[str] = field(default_factory=lambda: [
        "temperature", "humidity", "gas", "flame", "distance"
    ])


@dataclass
class ESP32CamConfig:
    """ESP32-CAM connection settings."""
    # ESP32-CAM stream URL (usually http://<ESP32_IP>/stream or /capture)
    stream_url: str = os.getenv("ESP32_CAM_URL", "http://192.168.1.100/capture")
    capture_interval: float = float(os.getenv("ESP32_CAPTURE_INTERVAL", "3.0"))
    timeout: float = 5.0
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0


@dataclass
class ActionControllerConfig:
    """GPIO relay control settings."""
    # GPIO pin numbers (BCM numbering)
    relay_pins: dict = field(default_factory=lambda: {
        "fan": int(os.getenv("GPIO_FAN_RELAY", "17")),
        "buzzer": int(os.getenv("GPIO_BUZZER", "27")),
        "light": int(os.getenv("GPIO_LIGHT_RELAY", "22")),
    })
    
    # Initial states (True = ON, False = OFF)
    initial_states: dict = field(default_factory=lambda: {
        "fan": False,
        "buzzer": False,
        "light": False,
    })
    
    # Relay logic (some relays are active-low)
    active_low: bool = bool(os.getenv("RELAY_ACTIVE_LOW", "True").lower() == "true")


@dataclass
class DetectionConfig:
    """Intruder detection settings."""
    confidence_threshold: float = float(os.getenv("DETECTION_CONFIDENCE", "0.5"))
    alert_cooldown: float = float(os.getenv("ALERT_COOLDOWN", "60.0"))
    target_classes: List[str] = field(default_factory=lambda: ["Human"])
    
    # Auto-action on intruder detection
    trigger_buzzer: bool = True
    buzzer_duration: float = 5.0


@dataclass
class BackendConfig:
    """FastAPI backend connection settings."""
    api_url: str = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")
    socketio_url: str = os.getenv("BACKEND_SOCKETIO_URL", "http://localhost:8000")
    
    # Authentication (for API calls)
    email: str = os.getenv("PI_USER_EMAIL", "pi@sensegrid.local")
    password: str = os.getenv("PI_USER_PASSWORD", "sensegrid123")
    
    # Device identification
    device_id: str = os.getenv("DEVICE_ID", "pi-main")
    room_id: str = os.getenv("ROOM_ID", "living-room")
    home_id: str = os.getenv("HOME_ID", "home-1")


@dataclass
class PiConfig:
    """Master configuration."""
    sensor_bridge: SensorBridgeConfig = field(default_factory=SensorBridgeConfig)
    esp32cam: ESP32CamConfig = field(default_factory=ESP32CamConfig)
    action_controller: ActionControllerConfig = field(default_factory=ActionControllerConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    
    # Run modes
    enable_sensors: bool = True
    enable_camera: bool = True
    enable_gpio: bool = True  # Disable on Windows for testing
    
    @classmethod
    def load(cls) -> "PiConfig":
        """Load configuration from environment."""
        return cls()


# Global config instance
config = PiConfig.load()
