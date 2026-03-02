# SenseGrid - Raspberry Pi Setup Guide

## Prerequisites

- Raspberry Pi 3/4/5 (or Zero 2 W)
- Raspberry Pi OS (64-bit recommended for Pi 4/5)
- Python 3.9+ 
- Node.js 18+
- Git

## Quick Install

```bash
# Clone the repository
git clone https://github.com/connectalamin/SenseGrid.git
cd SenseGrid

# Run setup script
./setup.sh
```

## Manual Installation

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Python 3.11 (if not available)
```bash
# Check current version
python3 --version

# If less than 3.9, install newer version
sudo apt install python3.11 python3.11-venv python3-pip -y
```

### 3. Install Node.js 18
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 4. Clone & Setup
```bash
git clone https://github.com/connectalamin/SenseGrid.git
cd SenseGrid

# Backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Generate secure JWT secret
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))" >> .env

# Frontend setup
cd ../frontend
npm install
cp .env.example .env
```

### 5. Configure for Network Access

Edit `backend/.env`:
```bash
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,http://192.168.1.XXX:5173
```

Edit `frontend/.env`:
```bash
VITE_API_URL=http://192.168.1.XXX:8000/api
VITE_WS_URL=http://192.168.1.XXX:8000
```

Replace `192.168.1.XXX` with your Raspberry Pi's IP address:
```bash
hostname -I
```

## Running the Application

### Development Mode

**Terminal 1 - Backend:**
```bash
cd ~/SenseGrid/backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd ~/SenseGrid/frontend
npm run dev -- --host
```

### Production Mode

**Build frontend:**
```bash
cd frontend
npm run build
```

**Serve with backend** (the backend can serve the built frontend):
```bash
cd backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Auto-Start on Boot (systemd)

### Backend Service

Create `/etc/systemd/system/sensegrid-backend.service`:

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

### Frontend Service (for dev mode)

Create `/etc/systemd/system/sensegrid-frontend.service`:

```bash
sudo nano /etc/systemd/system/sensegrid-frontend.service
```

```ini
[Unit]
Description=SenseGrid Frontend
After=network.target sensegrid-backend.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/SenseGrid/frontend
ExecStart=/usr/bin/npm run dev -- --host
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable sensegrid-backend
sudo systemctl enable sensegrid-frontend
sudo systemctl start sensegrid-backend
sudo systemctl start sensegrid-frontend
```

### Check Status

```bash
sudo systemctl status sensegrid-backend
sudo systemctl status sensegrid-frontend

# View logs
journalctl -u sensegrid-backend -f
journalctl -u sensegrid-frontend -f
```

## Firewall Configuration

If using `ufw`:
```bash
sudo ufw allow 8000  # Backend API
sudo ufw allow 5173  # Frontend dev server
sudo ufw allow 4173  # Frontend preview
```

## Accessing from Other Devices

1. Find your Raspberry Pi IP:
   ```bash
   hostname -I
   ```

2. Access from browser on same network:
   - Frontend: `http://<raspberry-pi-ip>:5173`
   - API Docs: `http://<raspberry-pi-ip>:8000/docs`

## Troubleshooting

### Database Issues
```bash
cd backend
rm sensegrid.db  # Delete and recreate
python -c "from database import init_db; init_db()"
```

### Permission Issues
```bash
sudo chown -R pi:pi ~/SenseGrid
```

### Port Already in Use
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

### Memory Issues on Pi Zero
```bash
# Increase swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Hardware Integration (Future)

For connecting actual sensors to your Raspberry Pi GPIO:

```python
# Example: Temperature sensor (DHT22)
# Install: pip install adafruit-circuitpython-dht
import adafruit_dht
import board

dht = adafruit_dht.DHT22(board.D4)
temperature = dht.temperature
humidity = dht.humidity
```

See `docs/hardware-integration.md` for detailed sensor setup.

## 🎯 Intruder Detection with TFLite (Recommended)

The TFLite detector is optimized for Raspberry Pi with INT8 quantized model (~3MB, fast inference).

### 1. Install TFLite Dependencies

```bash
cd ~/SenseGrid/backend
source .venv/bin/activate

# Install tflite-runtime (lightweight, Pi-optimized)
pip install tflite-runtime numpy opencv-python-headless
```

**Note:** Use `opencv-python-headless` on Pi (no GUI needed for server mode).

### 2. Configure Environment

Edit `backend/.env`:
```bash
# Use TFLite detector (recommended for Pi)
DETECTOR_TYPE=tflite

# Optional: custom model path (default: backend/models/best_int8.tflite)
# DETECTOR_MODEL_PATH=/path/to/your/model.tflite

# Detection confidence threshold
DETECTOR_CONFIDENCE=0.5
```

### 3. Verify Model File Exists

```bash
ls -la ~/SenseGrid/backend/models/best_int8.tflite
# Should show ~3MB file
```

### 4. Test Detection

```bash
cd ~/SenseGrid/backend
source .venv/bin/activate
python -c "from services.tflite_detector import get_detector; d = get_detector(); print('✅ TFLite ready!')"
```

Expected output:
```
✅ TFLite detector loaded: best_int8.tflite
   Input shape: [1, 416, 416, 3], dtype: int8
   Quantized: True
✅ TFLite ready!
```

### 5. Run with ESP32-CAM or USB Webcam

**Option A: ESP32-CAM (recommended for Pi headless)**
```bash
# Configure ESP32-CAM URL in .env
ESP32_CAM_URL=http://192.168.1.XX/capture

# Run the main Pi service
python hardware/pi_main.py
```

**Option B: USB Webcam**
```bash
# Test with webcam
python services/webcam_test.py
```

### TFLite vs Other Detectors

| Feature | TFLite (Pi) | Local YOLO | Roboflow Cloud |
|---------|-------------|------------|----------------|
| **RAM Usage** | ~50 MB | ~300 MB | ~30 MB |
| **Model Size** | 3 MB | 12 MB | None (cloud) |
| **Internet** | ❌ Not needed | ❌ Not needed | ✅ Required |
| **Speed (Pi 4)** | ~200-400ms | ~500ms+ | ~300-500ms |
| **Best For** | **Raspberry Pi** | Desktop+GPU | Cloud/Desktop |
