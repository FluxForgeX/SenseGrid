# SenseGrid - Raspberry Pi 5 Complete Setup Guide

A comprehensive guide to deploy SenseGrid IoT Dashboard on Raspberry Pi 5 (8GB).

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [System Architecture](#-system-architecture)
3. [Quick Start](#-quick-start)
4. [Detailed Setup](#-detailed-setup)
5. [Hardware Connections](#-hardware-connections)
6. [Configuration](#-configuration)
7. [Running the System](#-running-the-system)
8. [Auto-Start on Boot](#-auto-start-on-boot)
9. [Testing](#-testing)
10. [Troubleshooting](#-troubleshooting)

---

## 🔧 Prerequisites

### Hardware Required
- **Raspberry Pi 5** (4GB or 8GB recommended)
- **MicroSD Card** (32GB+ recommended)
- **Power Supply** (27W USB-C for Pi 5)
- **Arduino Uno** + Sensors (DHT11, MQ2, Flame, Ultrasonic)
- **ESP32-CAM** for camera/intruder detection
- **Relay Module** (2-4 channel) for actuators
- **USB Cable** (Arduino to Pi) or HC-05 Bluetooth module

### Software Required
- Raspberry Pi OS (64-bit, Bookworm or newer)
- Python 3.11+
- Node.js 18+
- Git

---

## 🏗 System Architecture

```
┌─────────────────┐     Serial/BT      ┌──────────────────┐
│  Arduino Uno    │ ─────────────────► │   Raspberry Pi   │
│  (Sensors)      │                    │   (pi_main.py)   │
│  - DHT11        │                    │                  │
│  - MQ2 Gas      │                    │   Backend API    │
│  - Flame        │                    │   (FastAPI)      │
│  - Ultrasonic   │                    │                  │
└─────────────────┘                    │   Frontend       │
                                       │   (React PWA)    │
┌─────────────────┐     HTTP/MJPEG     │                  │
│   ESP32-CAM     │ ─────────────────► │   TFLite Model   │
│   (Camera)      │                    │   (Detection)    │
└─────────────────┘                    └────────┬─────────┘
                                                │
┌─────────────────┐     GPIO            │
│   Relay Module  │ ◄───────────────────┘
│   - Fan         │
│   - Buzzer      │
│   - Light       │
└─────────────────┘
```

### Data Flow

1. **Sensors → Arduino → Pi**: Arduino reads sensors, sends JSON via Serial
2. **Pi → Backend**: `pi_main.py` parses data, sends via Socket.IO
3. **ESP32-CAM → Pi → TFLite**: Camera frames analyzed for intruders
4. **Backend → Frontend**: Real-time updates via Socket.IO
5. **Frontend → Backend → Pi → GPIO**: User controls actuators

---

## 🚀 Quick Start

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3-pip python3-venv nodejs npm git

# 3. Clone repository
git clone https://github.com/FluxForgeX/SenseGrid.git
cd SenseGrid

# 4. Run setup script
chmod +x setup.sh
./setup.sh

# 5. Start everything
./start.sh
```

---

## 📦 Detailed Setup

### Step 1: Update Raspberry Pi OS

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### Step 2: Install System Dependencies

```bash
# Python 3.11+ (usually pre-installed on Bookworm)
python3 --version  # Should show 3.11+

# If not available, install:
sudo apt install -y python3.11 python3.11-venv python3-pip

# Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version  # v18.x.x
npm --version   # 9.x.x

# Additional tools
sudo apt install -y git curl build-essential
```

### Step 3: Clone Repository

```bash
cd ~
git clone https://github.com/FluxForgeX/SenseGrid.git
cd SenseGrid
```

### Step 4: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install base dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install TFLite for Raspberry Pi (recommended detector)
pip install tflite-runtime numpy opencv-python-headless httpx

# Verify TFLite works
python -c "from services.tflite_detector import get_detector; d = get_detector(); print('✅ TFLite ready!')"
```

### Step 5: Frontend Setup

```bash
cd ~/SenseGrid/frontend

# Install npm dependencies
npm install

# Build for production (recommended for Pi)
npm run build

# The built files are in dist/ folder
```

### Step 6: Hardware Dependencies (GPIO)

```bash
# Install RPi.GPIO for relay control
pip install RPi.GPIO

# Add user to gpio group (if not using sudo)
sudo usermod -aG gpio $USER
```

---

## 🔌 Hardware Connections

### Arduino → Raspberry Pi (USB Serial)

| Arduino | Sensor |
|---------|--------|
| D2 | DHT11 Data |
| A0 | MQ2 Gas Analog |
| D3 | Flame Sensor Digital |
| D4 | Ultrasonic Trigger |
| D5 | Ultrasonic Echo |

Connect Arduino to Pi via USB cable. Usually appears as `/dev/ttyUSB0` or `/dev/ttyACM0`.

```bash
# Find Arduino port
ls /dev/tty* | grep -E "(USB|ACM)"
```

### Arduino Code

Upload this sketch to your Arduino:

```cpp
#include <DHT.h>

#define DHT_PIN 2
#define MQ2_PIN A0
#define FLAME_PIN 3
#define TRIG_PIN 4
#define ECHO_PIN 5

DHT dht(DHT_PIN, DHT11);

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(FLAME_PIN, INPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  int gas = analogRead(MQ2_PIN);
  int flame = digitalRead(FLAME_PIN);
  long distance = getDistance();
  
  // Send JSON to Raspberry Pi
  Serial.print("{\"temperature\":");
  Serial.print(isnan(temp) ? 0 : temp);
  Serial.print(",\"humidity\":");
  Serial.print(isnan(hum) ? 0 : hum);
  Serial.print(",\"gas\":");
  Serial.print(gas);
  Serial.print(",\"flame\":");
  Serial.print(flame);
  Serial.print(",\"distance\":");
  Serial.print(distance);
  Serial.println("}");
  
  delay(2000);
}

long getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  return duration / 58;
}
```

### ESP32-CAM Setup

1. Flash with **CameraWebServer** example (Arduino IDE)
2. Connect to same WiFi as Pi
3. Note the IP address (shown in Serial Monitor)
4. Test: Open `http://<ESP32_IP>/capture` in browser

### GPIO → Relay Module

| Raspberry Pi (BCM) | Physical Pin | Relay |
|-------------------|--------------|-------|
| GPIO 17 | Pin 11 | Fan |
| GPIO 27 | Pin 13 | Buzzer |
| GPIO 22 | Pin 15 | Light |
| 5V | Pin 2 | VCC |
| GND | Pin 6 | GND |

---

## ⚙️ Configuration

### Backend Configuration

Create `backend/.env`:

```bash
cd ~/SenseGrid/backend
nano .env
```

```bash
# JWT Authentication
JWT_SECRET=your-super-secret-key-at-least-32-characters-long

# Server
HOST=0.0.0.0
PORT=8000

# CORS (add your Pi's IP)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://192.168.1.XXX:5173

# Database (SQLite, auto-created)
DATABASE_URL=sqlite:///./sensegrid.db

# Detector Configuration
DETECTOR_TYPE=tflite
DETECTOR_CONFIDENCE=0.5

# ESP32-CAM (replace with your ESP32's IP)
ESP32_CAM_URL=http://192.168.1.XXX/capture
ESP32_CAM_STREAM_URL=http://192.168.1.XXX/stream
```

### Hardware Configuration

Create `hardware/.env`:

```bash
cd ~/SenseGrid/hardware
nano .env
```

```bash
# Arduino Serial Connection
ARDUINO_SERIAL_PORT=/dev/ttyUSB0
ARDUINO_BAUD_RATE=9600

# ESP32-CAM
ESP32_CAM_URL=http://192.168.1.XXX/capture
ESP32_CAPTURE_INTERVAL=3.0

# Backend Connection (localhost if running on same Pi)
BACKEND_API_URL=http://localhost:8000/api
BACKEND_SOCKETIO_URL=http://localhost:8000

# Pi Authentication (will be registered automatically)
PI_USER_EMAIL=pi@sensegrid.local
PI_USER_PASSWORD=sensegrid123

# Device Identification
DEVICE_ID=pi-main
ROOM_ID=living-room
HOME_ID=home-1

# GPIO Pins (BCM numbering)
GPIO_FAN_RELAY=17
GPIO_BUZZER=27
GPIO_LIGHT_RELAY=22
RELAY_ACTIVE_LOW=true
```

### Frontend Configuration

Create `frontend/.env`:

```bash
cd ~/SenseGrid/frontend
nano .env
```

```bash
# Backend API URL (use Pi's IP for network access)
VITE_API_URL=http://192.168.1.XXX:8000/api
VITE_WS_URL=http://192.168.1.XXX:8000
```

Then rebuild frontend:
```bash
npm run build
```

---

## ▶️ Running the System

### Option 1: Development Mode (Separate Terminals)

**Terminal 1 - Backend:**
```bash
cd ~/SenseGrid/backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend (Development):**
```bash
cd ~/SenseGrid/frontend
npm run dev -- --host
```

**Terminal 3 - Hardware Controller:**
```bash
cd ~/SenseGrid/hardware
source ../backend/.venv/bin/activate
python pi_main.py
```

### Option 2: Production Mode

```bash
# Start backend with production server
cd ~/SenseGrid/backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2

# Serve built frontend via nginx or backend static files
```

### Access Dashboard

From any device on the same network:
- **Dashboard**: `http://<PI_IP>:5173`
- **API Docs**: `http://<PI_IP>:8000/docs`
- **Camera Stream**: `http://<PI_IP>:8000/api/camera/stream?token=YOUR_TOKEN`

Find your Pi's IP:
```bash
hostname -I
```

---

## 🔄 Auto-Start on Boot

### Create systemd Services

**Backend Service:**
```bash
sudo nano /etc/systemd/system/sensegrid-backend.service
```

```ini
[Unit]
Description=SenseGrid Backend API
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/SenseGrid/backend
Environment=PATH=/home/pi/SenseGrid/backend/.venv/bin
ExecStart=/home/pi/SenseGrid/backend/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Hardware Controller Service:**
```bash
sudo nano /etc/systemd/system/sensegrid-hardware.service
```

```ini
[Unit]
Description=SenseGrid Hardware Controller
After=network.target sensegrid-backend.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/SenseGrid/hardware
Environment=PATH=/home/pi/SenseGrid/backend/.venv/bin
ExecStart=/home/pi/SenseGrid/backend/.venv/bin/python pi_main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable Services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable sensegrid-backend
sudo systemctl enable sensegrid-hardware
sudo systemctl start sensegrid-backend
sudo systemctl start sensegrid-hardware

# Check status
sudo systemctl status sensegrid-backend
sudo systemctl status sensegrid-hardware

# View logs
journalctl -u sensegrid-backend -f
journalctl -u sensegrid-hardware -f
```

---

## 🧪 Testing

### Test Backend
```bash
# Health check
curl http://localhost:8000/health

# API docs
curl http://localhost:8000/docs
```

### Test TFLite Detector
```bash
cd ~/SenseGrid/backend
source .venv/bin/activate
python -c "
from services.tflite_detector import get_detector
d = get_detector()
print('✅ Detector loaded successfully!')
"
```

### Test Arduino Connection
```bash
# Check if Arduino is detected
ls /dev/tty* | grep -E '(USB|ACM)'

# Read serial data
cat /dev/ttyUSB0  # Ctrl+C to stop
```

### Test ESP32-CAM
```bash
# Test capture endpoint
curl -o test.jpg http://192.168.1.XXX/capture
file test.jpg  # Should show JPEG image
```

### Test Camera Stream via Backend
```bash
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pi@sensegrid.local","password":"sensegrid123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Check camera status
curl http://localhost:8000/api/camera/status \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: tflite_runtime` | `pip install tflite-runtime` |
| Arduino not detected | Check USB, try `/dev/ttyACM0` |
| ESP32-CAM timeout | Verify IP, check WiFi connection |
| GPIO permission denied | `sudo usermod -aG gpio $USER` then logout/login |
| Port 8000 in use | `sudo lsof -i :8000` then `kill -9 <PID>` |
| Frontend not updating | Clear browser cache, check WebSocket |

### Check Logs
```bash
# Backend logs
journalctl -u sensegrid-backend -f

# Hardware logs
journalctl -u sensegrid-hardware -f

# System logs
dmesg | tail -50
```

### Memory Usage
```bash
# Check RAM usage
free -h

# Check running processes
htop
```

### Network Issues
```bash
# Find Pi's IP
hostname -I

# Check if port is open
sudo ss -tlnp | grep 8000

# Allow through firewall (if using ufw)
sudo ufw allow 8000
sudo ufw allow 5173
```

---

## 📊 Performance Tips for Pi 5

1. **Use built frontend** - Run `npm run build` instead of dev server
2. **Enable USB boot** - Faster than SD card
3. **Use TFLite** - Much lighter than full TensorFlow
4. **Disable desktop** - Use headless mode for more RAM
5. **Use ethernet** - More stable than WiFi for video streaming

---

## 📚 Additional Resources

- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [TensorFlow Lite for Pi](https://www.tensorflow.org/lite/guide/python)
- [ESP32-CAM Setup Guide](https://randomnerdtutorials.com/esp32-cam-video-streaming-web-server-camera-home-assistant/)

---

## 📝 License

MIT License - See [LICENSE](../LICENSE) for details.

---

**Happy Building! 🎉**

For issues or questions, open an issue on [GitHub](https://github.com/FluxForgeX/SenseGrid/issues).
