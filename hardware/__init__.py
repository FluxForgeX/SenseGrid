"""
SenseGrid Hardware Integration Layer

This package contains the Raspberry Pi side software that bridges:
- Arduino sensor data (via Serial/Bluetooth)
- ESP32-CAM image capture
- GPIO relay control
- FastAPI backend communication

Architecture:
    Sensors (Arduino) → sensor_bridge.py → backend (Socket.IO) → GUI
    ESP32-CAM → esp32cam_client.py → detection service → alerts
    Backend commands → action_controller.py → GPIO relays
"""
