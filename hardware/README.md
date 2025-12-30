# SenseGrid Hardware Integration

Hardware bridge layer for Raspberry Pi that connects Arduino sensors, ESP32-CAM, and GPIO relays to the SenseGrid backend.

## Architecture

```
Arduino (sensors) → sensor_bridge.py → Socket.IO → Backend → GUI
ESP32-CAM → esp32cam_client.py → Detection API → Alerts
Backend → action_controller.py → GPIO Relays
```

## Quick Start

### Windows Testing (No Hardware)
```powershell
cd hardware
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Test with all hardware disabled
python pi_main.py --no-sensors --no-camera --no-gpio
```

### Raspberry Pi Deployment

```bash
cd ~/SenseGrid/hardware
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install RPi.GPIO

# Configure
cp .env.example .env
nano .env  # Edit with your settings

# Test run
python pi_main.py

# Install as systemd service
sudo cp sensegrid.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sensegrid
sudo systemctl start sensegrid

# Check status
sudo systemctl status sensegrid
sudo journalctl -u sensegrid -f
```

## Configuration

Edit `.env` file:

```bash
# Arduino serial port (find with: ls /dev/tty*)
ARDUINO_SERIAL_PORT=/dev/ttyUSB0

# ESP32-CAM IP address
ESP32_CAM_URL=http://192.168.1.100/capture

# GPIO pins for relays
GPIO_FAN_RELAY=17
GPIO_BUZZER=27

# Backend URL
BACKEND_API_URL=http://localhost:8000/api
```

## Expected Arduino JSON Format

Your Arduino should send JSON lines over Serial/Bluetooth:

```json
{"temperature": 24.5, "humidity": 45, "gas": 120, "flame": 0, "distance": 50}
```

**No Arduino code changes needed** - the bridge reads whatever format your Arduino already sends.

## GPIO Wiring (Raspberry Pi)

| Component | GPIO Pin (BCM) | Physical Pin |
|-----------|----------------|--------------|
| Fan Relay | GPIO 17 | Pin 11 |
| Buzzer | GPIO 27 | Pin 13 |
| Light Relay | GPIO 22 | Pin 15 |
| Ground | GND | Pin 6, 9, 14, etc. |

## Services

### sensor_bridge.py
Reads Arduino sensor data via Serial/Bluetooth and forwards to backend.

### esp32cam_client.py
Captures frames from ESP32-CAM HTTP endpoint for intruder detection.

### action_controller.py
Controls GPIO relays (fan, buzzer, lights) based on backend commands.

### pi_main.py
Main orchestrator that runs all services and communicates with backend.

## Command Line Options

```bash
# Run without camera (test sensor bridge only)
python pi_main.py --no-camera

# Run without sensors (test camera only)
python pi_main.py --no-sensors

# Run without GPIO (Windows testing)
python pi_main.py --no-gpio

# Custom serial port
python pi_main.py --serial-port /dev/ttyACM0

# Custom ESP32 URL
python pi_main.py --esp32-url http://192.168.1.50/capture

# Custom backend URL
python pi_main.py --backend-url http://192.168.1.10:8000/api
```

## Troubleshooting

### Serial port not found
```bash
# List available ports
ls /dev/tty*

# Check permissions
sudo usermod -a -G dialout $USER
# Then log out and back in
```

### ESP32-CAM not responding
- Check ESP32 is powered and on same network
- Test URL in browser: `http://<ESP32_IP>/capture`
- Verify ESP32 firmware is configured for HTTP mode

### GPIO not working
```bash
# Check if RPi.GPIO is installed
python -c "import RPi.GPIO; print('OK')"

# Check permissions
sudo usermod -a -G gpio $USER
```

### Backend connection failed
- Ensure backend is running: `sudo systemctl status sensegrid-backend`
- Check firewall: `sudo ufw allow 8000`
- Verify backend URL in `.env`

## Integration with Main Backend

The hardware layer communicates with the FastAPI backend via:

1. **Socket.IO** (real-time sensor data)
   - Emits `device_update` with sensor readings
   - Listens for `action:command` and `action:update`

2. **REST API** (intruder detection)
   - POST `/api/intruder/detect` with camera frames
   - Uses JWT authentication

3. **Auto-actions** (local decisions)
   - High gas → turn on fan
   - Flame detected → trigger buzzer
   - High temperature → turn on fan

## License

Part of SenseGrid project.
