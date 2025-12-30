"""
Sensor Bridge - Reads Arduino data via Serial/Bluetooth

Expects Arduino to send JSON lines like:
    {"temperature": 24.5, "humidity": 45, "gas": 120, "flame": 0, "distance": 50}

Does NOT modify Arduino behavior - just reads what Arduino sends.
"""

import json
import time
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import serial

from config import SensorBridgeConfig


@dataclass
class SensorData:
    """Parsed sensor reading from Arduino."""
    temperature: float = 0.0
    humidity: float = 0.0
    gas: int = 0
    flame: int = 0
    distance: float = 0.0
    timestamp: float = 0.0
    raw: Dict[str, Any] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "SensorData":
        return cls(
            temperature=float(data.get("temperature", 0)),
            humidity=float(data.get("humidity", 0)),
            gas=int(data.get("gas", 0)),
            flame=int(data.get("flame", 0)),
            distance=float(data.get("distance", 0)),
            timestamp=time.time(),
            raw=data
        )


class SensorBridge:
    """
    Reads sensor data from Arduino via Serial/Bluetooth.
    
    Thread-safe, runs in background, calls callback on new data.
    """
    
    def __init__(
        self,
        config: Optional[SensorBridgeConfig] = None,
        on_data: Optional[Callable[[SensorData], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.config = config or SensorBridgeConfig()
        self.on_data = on_data
        self.on_error = on_error
        
        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_data: Optional[SensorData] = None
        self._lock = threading.Lock()
        self._read_count = 0
        self._error_count = 0
    
    def _connect(self) -> bool:
        """Establish serial connection to Arduino."""
        try:
            self._serial = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=self.config.timeout
            )
            # Wait for Arduino to reset after connection
            time.sleep(2)
            # Clear any buffered data
            self._serial.reset_input_buffer()
            print(f"[sensor_bridge] ✅ Connected to {self.config.serial_port} @ {self.config.baud_rate} baud")
            return True
        except Exception as e:
            print(f"[sensor_bridge] ❌ Failed to connect: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    def _parse_line(self, line: str) -> Optional[SensorData]:
        """Parse a JSON line from Arduino."""
        try:
            line = line.strip()
            if not line or not line.startswith("{"):
                return None
            
            data = json.loads(line)
            return SensorData.from_dict(data)
        except json.JSONDecodeError as e:
            # Arduino might send partial lines or debug messages
            print(f"[sensor_bridge] ⚠️ Parse error: {e} - Line: {line[:50]}")
            return None
    
    def _read_loop(self):
        """Main reading loop (runs in background thread)."""
        print("[sensor_bridge] 🎥 Starting read loop...")
        
        while self._running:
            try:
                if self._serial is None or not self._serial.is_open:
                    if not self._connect():
                        time.sleep(5)  # Wait before retry
                        continue
                
                # Read line from Arduino
                line = self._serial.readline().decode('utf-8', errors='ignore')
                
                if not line:
                    continue
                
                # Parse sensor data
                sensor_data = self._parse_line(line)
                
                if sensor_data:
                    self._read_count += 1
                    
                    with self._lock:
                        self._latest_data = sensor_data
                    
                    # Log periodically
                    if self._read_count % 10 == 0:
                        print(f"[sensor_bridge] 📡 T={sensor_data.temperature:.1f}°C, "
                              f"H={sensor_data.humidity:.0f}%, G={sensor_data.gas}, "
                              f"F={sensor_data.flame}, D={sensor_data.distance:.0f}cm")
                    
                    # Callback
                    if self.on_data:
                        try:
                            self.on_data(sensor_data)
                        except Exception as e:
                            print(f"[sensor_bridge] ⚠️ Callback error: {e}")
                            
            except serial.SerialException as e:
                self._error_count += 1
                print(f"[sensor_bridge] ❌ Serial error: {e}")
                if self._serial:
                    self._serial.close()
                    self._serial = None
                time.sleep(2)
            except Exception as e:
                self._error_count += 1
                print(f"[sensor_bridge] ❌ Error: {e}")
                if self.on_error:
                    self.on_error(e)
                time.sleep(1)
        
        print("[sensor_bridge] 🛑 Read loop stopped")
    
    def start(self) -> bool:
        """Start the sensor bridge."""
        if self._running:
            return True
        
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        
        print("[sensor_bridge] ✅ Started")
        return True
    
    def stop(self):
        """Stop the sensor bridge."""
        if not self._running:
            return
        
        print("[sensor_bridge] Stopping...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None
        
        print("[sensor_bridge] ✅ Stopped")
    
    def get_latest(self) -> Optional[SensorData]:
        """Get the most recent sensor reading."""
        with self._lock:
            return self._latest_data
    
    def get_stats(self) -> dict:
        """Get bridge statistics."""
        return {
            "running": self._running,
            "connected": self._serial is not None and self._serial.is_open,
            "read_count": self._read_count,
            "error_count": self._error_count,
            "port": self.config.serial_port,
        }
    
    @property
    def is_running(self) -> bool:
        return self._running
