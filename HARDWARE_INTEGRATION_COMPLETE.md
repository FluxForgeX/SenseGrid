# 🎯 SenseGrid Hardware Integration - Implementation Complete

## ✅ What's Been Implemented

### 1. Hardware Bridge Architecture
Complete software layer that connects your existing Arduino + ESP32-CAM hardware to the SenseGrid backend **without modifying any Arduino code**.

```
┌────────────────────────────────────────────────────────────────┐
│                    SENSEGRID FULL SYSTEM                        │
└────────────────────────────────────────────────────────────────┘

Physical Layer (UNCHANGED)
    Arduino + Sensors (DHT11, MQ-9, Flame, HC-SR04)
           ↓ Serial/Bluetooth
    
Software Bridge (NEW)
    ├── sensor_bridge.py      → Reads Arduino JSON
    ├── esp32cam_client.py    → Captures ESP32-CAM frames
    ├── action_controller.py  → Controls GPIO relays
    └── pi_main.py            → Orchestrates everything
           ↓ Socket.IO + REST
    
Backend Layer (EXISTING)
    ├── FastAPI + SQLite
    ├── Roboflow Detection API
    ├── Socket.IO real-time
    └── JWT Authentication
           ↓ WebSocket
    
GUI Layer (EXISTING)
    React PWA with offline-first architecture
```

---

## 📁 Files Created

### Core Hardware Services

| File | Purpose | Lines |
|------|---------|-------|
| `hardware/config.py` | Configuration management | 120 |
| `hardware/sensor_bridge.py` | Arduino data reader | 180 |
| `hardware/esp32cam_client.py` | ESP32-CAM frame capture | 150 |
| `hardware/action_controller.py` | GPIO relay control | 200 |
| `hardware/pi_main.py` | Main orchestrator | 350 |

### Supporting Files

| File | Purpose |
|------|---------|
| `hardware/.env.example` | Configuration template |
| `hardware/requirements.txt` | Python dependencies |
| `hardware/sensegrid.service` | Systemd service file |
| `hardware/README.md` | Deployment guide |
| `hardware/register_pi_user.py` | User registration |

---

## 🔧 How It Works

### Sensor Data Flow
1. Arduino sends JSON over Serial: `{"temperature": 24.5, "humidity": 45, "gas": 120, "flame": 0, "distance": 50}`
2. `sensor_bridge.py` reads and parses the data
3. Forwards to backend via Socket.IO `device_update` event
4. Backend stores in database
5. Real-time broadcast to GUI via `sensorUpdate` event
6. GUI displays in room cards

### Intruder Detection Flow
1. ESP32-CAM captures frame every 3 seconds
2. `esp32cam_client.py` fetches via HTTP
3. Sends to backend `/api/intruder/detect` endpoint
4. Backend calls Roboflow API for detection
5. If Human detected → Alert created
6. Socket.IO broadcasts `intruder:alert`
7. Optional: GPIO buzzer triggered locally

### Action Control Flow
1. User toggles fan in GUI
2. Backend emits `action:command` via Socket.IO
3. `pi_main.py` receives command
4. `action_controller.py` sets GPIO pin
5. Physical relay activates
6. State synced back to database

---

## 🚀 Deployment Guide

### Prerequisites
- ✅ Raspberry Pi 5 with Raspberry Pi OS
- ✅ Arduino (already programmed, no changes)
- ✅ ESP32-CAM on same network
- ✅ Backend running (FastAPI + Socket.IO)

### Step 1: Copy Files to Pi
```bash
# On your development machine
scp -r SenseGrid pi@raspberrypi.local:~/

# SSH into Pi
ssh pi@raspberrypi.local
cd ~/SenseGrid/hardware
```

### Step 2: Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install RPi.GPIO
```

### Step 3: Configure
```bash
cp .env.example .env
nano .env
```

Edit these values:
```bash
ARDUINO_SERIAL_PORT=/dev/ttyUSB0  # Find with: ls /dev/tty*
ESP32_CAM_URL=http://192.168.1.100/capture  # Your ESP32 IP
BACKEND_API_URL=http://localhost:8000/api
PI_USER_EMAIL=pi@sensegrid.local
PI_USER_PASSWORD=sensegrid123
```

### Step 4: Register Pi User
```bash
# Make sure backend is running first
python register_pi_user.py
```

### Step 5: Test Run
```bash
python pi_main.py
```

You should see:
```
============================================================
SenseGrid Raspberry Pi Controller
============================================================
[pi_main] ✅ Authenticated as pi@sensegrid.local
[pi_main] ✅ Connected to backend Socket.IO
[action_controller] ✅ GPIO initialized
[sensor_bridge] ✅ Connected to /dev/ttyUSB0 @ 9600 baud
[esp32cam] ✅ Connection OK, frame size: 45821 bytes
[pi_main] ✅ All services started
============================================================
```

### Step 6: Install as Service (Auto-start on boot)
```bash
sudo cp sensegrid.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sensegrid
sudo systemctl start sensegrid

# Check status
sudo systemctl status sensegrid

# View logs
sudo journalctl -u sensegrid -f
```

---

## 🧪 Testing on Windows (Before Pi Deployment)

You can test the software on Windows with hardware disabled:

```powershell
cd hardware
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Test with all hardware disabled
python pi_main.py --no-sensors --no-camera --no-gpio
```

This will:
- ✅ Connect to backend Socket.IO
- ✅ Authenticate
- ✅ Use Mock GPIO (prints to console)
- ❌ Skip Serial/Camera (not connected)

---

## 🔌 GPIO Wiring Reference

| Component | GPIO (BCM) | Physical Pin | Notes |
|-----------|------------|--------------|-------|
| Fan Relay IN | 17 | Pin 11 | Controls main fan |
| Buzzer | 27 | Pin 13 | Intruder alarm |
| Light Relay IN | 22 | Pin 15 | Optional |
| Ground | GND | Pin 6, 9, 14 | Common ground |
| 5V Power | 5V | Pin 2, 4 | For relay module VCC |

**Relay Module Connections:**
- VCC → 5V (Pin 2)
- GND → GND (Pin 6)
- IN1 → GPIO 17 (Pin 11)
- IN2 → GPIO 27 (Pin 13)
- COM → Fan/Device positive wire
- NO → Power source positive

---

## 📡 Expected Arduino JSON Format

Your Arduino should already be sending this format (no changes needed):

```json
{"temperature": 24.5, "humidity": 45, "gas": 120, "flame": 0, "distance": 50}
```

If your format is different, edit `sensor_bridge.py` → `SensorData.from_dict()` to match your field names.

---

## 🎛️ Configuration Options

### Serial Port Detection
```bash
# List all serial devices
ls /dev/tty*

# Likely candidates:
# /dev/ttyUSB0  → USB-to-Serial adapter
# /dev/ttyACM0  → Arduino direct USB
# /dev/rfcomm0  → Bluetooth connection
```

### ESP32-CAM URL Formats
```bash
# Single capture endpoint (recommended)
ESP32_CAM_URL=http://192.168.1.100/capture

# MJPEG stream endpoint (if supported)
ESP32_CAM_URL=http://192.168.1.100/stream

# Custom port
ESP32_CAM_URL=http://192.168.1.100:8080/cam
```

### Capture Intervals
```bash
# Fast detection (higher CPU/bandwidth)
ESP32_CAPTURE_INTERVAL=2.0
WEBCAM_CAPTURE_INTERVAL=3.0

# Balanced (recommended)
ESP32_CAPTURE_INTERVAL=3.0
WEBCAM_CAPTURE_INTERVAL=5.0

# Power saving (slower response)
ESP32_CAPTURE_INTERVAL=10.0
WEBCAM_CAPTURE_INTERVAL=10.0
```

### Alert Cooldown
```bash
# Quick re-alert (testing)
ALERT_COOLDOWN=10.0

# Production (avoid spam)
ALERT_COOLDOWN=60.0

# Very conservative
ALERT_COOLDOWN=300.0  # 5 minutes
```

---

## 🐛 Troubleshooting

### Issue: Serial port permission denied
**Solution:**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Issue: ESP32-CAM not responding
**Check:**
1. Ping ESP32: `ping 192.168.1.100`
2. Test URL in browser: `http://192.168.1.100/capture`
3. Check ESP32 firmware settings (HTTP mode enabled)
4. Verify power supply (ESP32-CAM needs stable 5V)

### Issue: GPIO not working
**Solution:**
```bash
# Check permissions
sudo usermod -a -G gpio $USER

# Verify RPi.GPIO installed
python -c "import RPi.GPIO; print('OK')"

# Check pin states
gpio readall
```

### Issue: Backend connection failed
**Check:**
1. Backend running: `sudo systemctl status sensegrid-backend`
2. Network: `curl http://localhost:8000/api/health`
3. Firewall: `sudo ufw allow 8000`
4. .env file has correct URL

### Issue: No sensor data in GUI
**Check:**
1. `sensor_bridge` connected: Check logs
2. Socket.IO connected: Look for "Connected to backend"
3. Backend receiving data: Check backend logs
4. Database updated: Query rooms table

---

## 🎯 What Happens When You Run pi_main.py

1. **Startup (5-10 seconds)**
   - Loads configuration from `.env`
   - Authenticates with backend (JWT token)
   - Connects to Socket.IO server
   - Initializes GPIO pins (sets all to OFF)
   - Opens Serial connection to Arduino
   - Tests ESP32-CAM connection

2. **Sensor Loop (continuous)**
   - Reads Arduino JSON every time data arrives
   - Parses temperature, humidity, gas, flame, distance
   - Forwards to backend via `device_update` event
   - Checks auto-action thresholds locally
   - Logs summary every 10 readings

3. **Camera Loop (every 3 seconds)**
   - Fetches frame from ESP32-CAM
   - Checks alert cooldown (60 seconds default)
   - Sends to `/api/intruder/detect` endpoint
   - If Human detected → Triggers buzzer
   - Logs detection results

4. **Action Listener (event-driven)**
   - Listens for `action:command` from backend
   - Receives fan/buzzer/light commands from GUI
   - Sets GPIO pins accordingly
   - Logs state changes

---

## 🔄 Integration Points

### Backend ↔ Pi Communication

| Event | Direction | Data | Purpose |
|-------|-----------|------|---------|
| `device_update` | Pi → Backend | Sensor readings | Forward Arduino data |
| `action:command` | Backend → Pi | Action state | Control relays from GUI |
| `action:update` | Backend → Pi | Action state | Legacy format support |
| `device_register` | Pi → Backend | Device info | Identify Pi on connect |

### REST API Calls

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | Get JWT token |
| `/api/intruder/detect` | POST | Submit frame for detection |

---

## 📊 Expected Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Sensor read rate | 1-2 Hz | Depends on Arduino |
| Camera capture rate | 0.33 Hz | Every 3 seconds |
| Detection latency | 1-3s | Roboflow API call |
| GPIO response time | <100ms | Near instant |
| Socket.IO latency | 10-50ms | Local network |
| Memory usage | ~150 MB | Python + services |
| CPU usage | 5-15% | Raspberry Pi 5 |

---

## ✅ Verification Checklist

Before deploying to production:

- [ ] Backend is running and accessible
- [ ] Pi user registered (`register_pi_user.py`)
- [ ] Arduino sending JSON over Serial
- [ ] ESP32-CAM responding to HTTP requests
- [ ] GPIO pins wired correctly (check with multimeter)
- [ ] `.env` file configured with correct values
- [ ] Test run successful (`python pi_main.py`)
- [ ] Sensor data visible in GUI
- [ ] Camera frames triggering detection
- [ ] Relay toggle from GUI works
- [ ] Systemd service installed and enabled
- [ ] Auto-start on reboot tested

---

## 🎉 Summary

You now have a **complete, production-ready hardware integration layer** that:

✅ Reads Arduino sensors without modifying Arduino code  
✅ Captures ESP32-CAM frames for AI detection  
✅ Controls GPIO relays based on sensor thresholds and GUI commands  
✅ Communicates with backend via Socket.IO and REST API  
✅ Works on Windows (testing) and Raspberry Pi (production)  
✅ Auto-starts on boot via systemd service  
✅ Modular, maintainable, well-documented  

**Next steps:**
1. Test on Windows: `python pi_main.py --no-sensors --no-camera --no-gpio`
2. Deploy to Pi following the guide above
3. Monitor logs: `sudo journalctl -u sensegrid -f`
4. Enjoy your fully integrated IoT home automation system! 🏠🤖
