# 🚨 SenseGrid Intruder Detection Integration

## ✅ Integration Complete - Roboflow Cloud API

Your FastAPI backend now has **cloud-based intruder detection** using **Roboflow's serverless inference API**.

**Key Benefits:**
- ✅ No model files to manage
- ✅ Works on Windows and Raspberry Pi (with internet)
- ✅ Automatic scaling and reliability
- ✅ Easy model updates via Roboflow dashboard
- ✅ Lower memory footprint
- ✅ Swappable architecture (can switch to local YOLO later)

---

## 📋 What Was Added

### 1. **Directory Structure**
```
backend/
├── services/
│   ├── __init__.py
│   ├── intruder_detector.py      ← Abstract interface
│   ├── roboflow_detector.py       ← Roboflow Cloud API (PRIMARY)
│   ├── local_yolo_detector.py     ← Local YOLO (ALTERNATIVE)
│   └── webcam_test.py
├── models/
│   └── (no files needed for Roboflow)
```

### 2. **Dependencies Added to requirements.txt**
- `inference-sdk` - Roboflow Cloud API client (PRIMARY)
- `ultralytics` - Local YOLO (commented out, optional)
- `opencv-python` - Local YOLO (commented out, optional)

### 3. **New API Endpoint**
```
POST /api/intruder/detect
```
Accepts image upload, runs Roboflow inference, creates alerts, emits Socket.IO events.

---

## 🚀 Setup Instructions

### Step 1: Get Roboflow Credentials

1. **Log in to Roboflow:** https://app.roboflow.com
2. **Copy your API key** from Settings → Roboflow API
3. **Note your workspace name** (e.g., "project-ark")
4. **Note your workflow ID** (e.g., "custom-workflow-2")

---

### Step 2: Configure Environment Variables

Edit `backend/.env` (or create from `.env.example`):

```bash
# Roboflow Cloud API Configuration
ROBOFLOW_API_KEY=qrZbvOPZvnXOGW9UzKbG
ROBOFLOW_WORKSPACE=project-ark
ROBOFLOW_WORKFLOW_ID=custom-workflow-2
ROBOFLOW_CONFIDENCE=0.6

# Detector Type (use 'roboflow' for cloud API)
DETECTOR_TYPE=roboflow
```

**CRITICAL:** Do NOT commit your `.env` file with real API keys to Git!

---

### Step 3: Install Dependencies

Make sure you're in the backend directory with your virtual environment activated:

```powershell
cd backend

# Activate virtual environment (if not already active)
.\.venv311\Scripts\activate

# Install new dependencies
pip install -r requirements.txt
```

This will install:
- `inference-sdk` - Roboflow API client
- All required dependencies

---

### Step 4: Start the Backend

```powershell
# From backend directory with venv active
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Expected startup log:**
```
✅ Roboflow detector initialized
   Workspace: project-ark
   Workflow: custom-workflow-2
   Confidence threshold: 0.6
[startup] Initializing database...
[startup] Database initialized successfully
INFO:     Application startup complete.
```

❌ If you see errors about missing API key, check Step 2.

---

## 🧪 Testing the API Endpoint

### Option 1: Using cURL (Windows PowerShell)

```powershell
# Get auth token first
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"your@email.com","password":"yourpassword"}'
$token = $response.token

# Test detection with an image
Invoke-RestMethod -Uri "http://localhost:8000/api/intruder/detect" `
  -Method POST `
  -Headers @{"Authorization"="Bearer $token"} `
  -Form @{file=Get-Item "path\to\test-image.jpg"}
```

### Option 2: Using Python Script

Create `test_detection.py` in backend/:

```python
import requests

# Login
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "your@email.com", "password": "yourpassword"}
)
token = login_response.json()["token"]

# Test detection
with open("test-image.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/intruder/detect",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )

print(response.json())
```

Run it:
```powershell
python test_detection.py
```

### Expected Response

**If human detected:**
```json
{
  "intruder_detected": true,
  "detections": [
    {
      "class": "Human",
      "confidence": 0.87,
      "bbox": {"x": 320, "y": 240, "width": 100, "height": 200}
    }
  ],
  "alert_id": "alert-1735574400000",
  "detection_count": 1,
  "detector_type": "roboflow"
}
```

**If no human:**
```json
{
  "intruder_detected": false,
  "detections": [],
  "alert_id": null,
  "detection_count": 0,
  "detector_type": "roboflow"
}
```

---

## 🔄 Switching Between Cloud and Local Detection

The system supports both Roboflow Cloud API and local YOLO models through a swappable architecture.

### Using Roboflow Cloud API (Default - Requires Internet)

**Advantages:**
- ✅ No model files to manage
- ✅ Works immediately after setup
- ✅ Automatic scaling
- ✅ Easy model updates

**Setup:**
1. Set `DETECTOR_TYPE=roboflow` in `.env`
2. Configure Roboflow credentials (see Step 2)
3. Install `inference-sdk`

### Using Local YOLO Model (Optional - Works Offline)

**Advantages:**
- ✅ Works without internet
- ✅ Faster inference (no API latency)
- ✅ More privacy (no data leaves device)

**Setup:**
1. Place `best.pt` model in `backend/models/`
2. Uncomment `ultralytics` and `opencv-python` in `requirements.txt`
3. Install: `pip install ultralytics opencv-python`
4. Set `DETECTOR_TYPE=local` in `.env`
5. Restart backend

**Test local detector:**
```powershell
python services\webcam_test.py
```

---

## 🔌 Frontend Integration (Optional)

The endpoint is ready for frontend use. Example API call:

```javascript
// In frontend/src/services/api.js

export async function uploadIntruderImage(imageFile) {
  const formData = new FormData()
  formData.append('file', imageFile)
  
  const response = await axios.post('/intruder/detect', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  
  return response.data
}
```

**Socket.IO Event Handling:**

The backend emits `intruder:alert` events when humans are detected. Frontend already has Socket.IO integration in `socket.jsx`.

---

## 📊 How It Works

### Detection Flow

```
1. Client uploads image to POST /api/intruder/detect
   ↓
2. Backend saves to temp file
   ↓
3. IntruderDetector.detect_from_image() runs YOLO
   ↓
4. If "Human" class detected:
   - Creates alert in database
   - Emits Socket.IO event → Frontend shows notification
   - Returns detection details
   ↓
5. Temp file cleaned up
   ↓
6. Response returned to client
```

### Key Features

✅ **Fully Offline** - No Roboflow API, no internet required
✅ **Low Latency** - Direct YOLO inference (~100-500ms on CPU)
✅ **Database Integration** - Alerts stored in SQLite
✅ **Real-time Notifications** - Socket.IO events to all connected clients
✅ **Multi-user Support** - Each user has isolated alerts
✅ **Confidence Threshold** - Default 0.5 (50% confidence)

---

## 🔧 Configuration Options

### Adjust Confidence Threshold

Edit `backend/services/intruder_detector.py`:

```python
# Change default confidence (0.5 = 50%)
detections = detector.detect_from_image(temp_path, conf=0.6, iou=0.35)
```

Lower = more detections (more false positives)
Higher = fewer detections (more false negatives)

### Change Detection Class

If your model detects other classes:

```python
# In intruder_detector.py, line 89
if label == "Person":  # or "Intruder", "Face", etc.
```

---

## 🐛 Troubleshooting

### "Model not found" Error

**Cause:** `best.pt` not in `backend/models/`

**Fix:**
```powershell
# Check if file exists
dir backend\models\best.pt

# If not, copy it
copy path\to\best.pt backend\models\best.pt
```

---

### Import Error: "No module named 'ultralytics'"

**Cause:** Dependencies not installed

**Fix:**
```powershell
cd backend
pip install -r requirements.txt
```

---

### "Webcam not accessible"

**Cause:** Another app is using the camera

**Fix:**
- Close Zoom, Teams, Skype, etc.
- Try changing camera index in `webcam_test.py`:
  ```python
  cap = cv2.VideoCapture(1)  # Try 1, 2, 3...
  ```

---

### Slow Inference Speed

**Cause:** Running on CPU

**Improvement Options:**
1. **Use smaller image resolution** (faster but less accurate)
2. **GPU acceleration** (requires CUDA-compatible GPU + pytorch with CUDA)
3. **Optimize model** (export to ONNX or TensorRT)

For GPU support:
```powershell
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## 🚀 Next Steps

### 1. Integration with Raspberry Pi Camera

Copy the backend folder to Raspberry Pi and install:

```bash
# On Raspberry Pi
cd backend
pip install -r requirements.txt

# Test with PiCamera
python services/webcam_test.py  # Will use Pi camera if available
```

### 2. Continuous Monitoring Script

Create `services/monitor.py`:

```python
from intruder_detector import get_detector
import cv2
import time

detector = get_detector()
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    detections = detector.detect_from_frame(frame, conf=0.6)
    
    if detections:
        print(f"🚨 {len(detections)} human(s) detected")
        # Here: Call API to create alert
        # or directly emit Socket.IO event
    
    time.sleep(5)  # Check every 5 seconds
```

### 3. Save Detection Images

Modify endpoint to save snapshot:

```python
# In main.py, after detection
if detections:
    snapshot_path = f"snapshots/{alert_id}.jpg"
    os.makedirs("snapshots", exist_ok=True)
    shutil.copy(temp_path, snapshot_path)
    
    new_alert.snapshot_url = f"/snapshots/{alert_id}.jpg"
```

---

## ✅ Verification Checklist

Before moving to production:

- [ ] `best.pt` is in `backend/models/`
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Webcam test works (`python services\webcam_test.py`)
- [ ] Backend starts without errors
- [ ] API endpoint returns detections
- [ ] Socket.IO events emitted when humans detected
- [ ] Alerts saved to database

---

## 📚 Related Files

- [backend/services/intruder_detector.py](backend/services/intruder_detector.py) - Detection service
- [backend/services/webcam_test.py](backend/services/webcam_test.py) - Local test script
- [backend/main.py](backend/main.py) - API endpoint (line ~470)
- [backend/requirements.txt](backend/requirements.txt) - Dependencies

---

## 🎯 Summary

✅ **Local YOLO model** (`best.pt`) is now integrated
✅ **No Roboflow API** dependency at runtime
✅ **Works offline** on Windows laptop
✅ **Ready for Raspberry Pi** deployment (no code changes needed)
✅ **Tested with webcam** script included

**Next:** Place your `best.pt` file and run the tests! 🚀
