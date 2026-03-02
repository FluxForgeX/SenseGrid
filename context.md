# SenseGrid — AI Agent Context

> **Purpose of this file**: If you open this project on a new PC or in a new AI session, read this first. It captures everything that has been built, all decisions made, the current state, and exactly what to do next.

---

## What This Project Is

**SenseGrid** is a mobile-first PWA for IoT room security. It includes:
- A **React frontend** (Vite + Tailwind + Zustand + Socket.IO)
- A **FastAPI backend** (Python, SQLAlchemy, Socket.IO)
- A **Raspberry Pi** client that captures camera frames and sends them to the backend
- A **YOLOv8n** person detection model (custom-trained via Google Colab)
- A **DeepFace/ArcFace** face recognition layer (server-side, to skip authorized people)

---

## Architecture Overview

```
Raspberry Pi (ESP32-CAM)
  └─ captures frames
  └─ HTTP POST /api/intruder/detect → Backend Server (your PC)
        └─ YOLO detects "Human"
        └─ DeepFace/ArcFace checks each detected person's face
              ├─ "authorized" → skip, no alert
              ├─ "intruder"   → create DB alert + Socket.IO event
              ├─ "no_face"    → alert (person seen from behind / too far)
              └─ "unavailable"→ alert (Pi fallback mode, DeepFace not installed)
        └─ Frontend receives Socket.IO "intruder:alert" → shows notification
```

**The Pi never runs ML models.** It only captures frames and POSTs them. All inference happens on the backend server.

---

## Repository Structure (key files)

```
SenseGrid/
├── backend/
│   ├── main.py                        ← FastAPI app, ALL endpoints
│   ├── database.py                    ← SQLAlchemy models (User, Room, Alert)
│   ├── requirements.txt               ← Python deps (see "Environment" section)
│   ├── models/
│   │   ├── best.pt                    ← YOLOv8n trained model (download from Colab)
│   │   └── known_faces.json           ← Enrolled authorized faces (auto-created)
│   └── services/
│       ├── face_recognizer.py         ← DeepFace/ArcFace face recognition service ★ NEW
│       ├── local_yolo_detector.py     ← YOLO-based person detector (uses best.pt)
│       ├── roboflow_detector.py       ← Roboflow cloud API detector (alt)
│       └── intruder_detector.py       ← Abstract base class / factory
├── frontend/
│   └── src/
│       ├── components/RoomCard.jsx    ← Main sensor card with optimistic UI
│       ├── services/offlineQueue.js   ← IndexedDB offline command queue
│       └── store/useStore.js          ← Zustand global state
├── hardware/
│   ├── pi_main.py                     ← Raspberry Pi controller
│   └── esp32cam_client.py             ← Camera frame capture
└── model.ipynb                        ← Google Colab training notebook (YOLO only)
```

---

## Environment Setup

### On your development PC

```powershell
# Create and activate the dedicated environment (Python 3.11)
conda create -n sensegrid python=3.11 -y
conda activate sensegrid

# Install all dependencies (including face recognition)
cd i:\Web\Academic\SenseGrid\backend
pip install -r requirements.txt
```

> ⚠️ **Do NOT use the `venv` conda environment** for this project — it has conflicting package versions that will break face recognition. Always use `sensegrid`.

### On Raspberry Pi

```bash
# Pi only needs the lightweight deps — DeepFace is too heavy for Pi
pip install fastapi uvicorn python-multipart python-jose bcrypt \
    python-dotenv python-socketio aiofiles sqlalchemy inference-sdk
# NO deepface / tf-keras on Pi — the backend auto-detects and falls back gracefully
```

---

## Running the Backend

```powershell
conda activate sensegrid
cd i:\Web\Academic\SenseGrid\backend
$env:DETECTOR_TYPE = "local"     # use local YOLO (needs best.pt)
# OR
$env:DETECTOR_TYPE = "roboflow"  # use Roboflow cloud API (needs API key)

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

---

## YOLO Model (best.pt)

**Status: Not downloaded yet.** The model must be trained in Google Colab first.

### To train and get the model:
1. Open `model.ipynb` in **Google Colab** (not locally)
2. Run all cells in order (Cell 1 → Cell 9)
3. After training, download `raspberry_pi_model.zip` from Colab
4. Extract and copy `best.pt` to `backend/models/best.pt`

### Model details:
- Architecture: YOLOv8n (Nano, ~6MB)
- Dataset: Roboflow `intruder_batch1-eu8c6` version 9
- Training: 100 epochs, imgsz=416, batch=32
- Target: 75–80% mAP50
- TFLite export (`best.tflite`) also generated for Pi deployment

---

## Face Recognition System ★ NEW

### What was built
A complete face recognition pipeline in `backend/services/face_recognizer.py`:
- Uses **DeepFace + ArcFace** model (512-dim embeddings, ~250MB, auto-downloaded on first use)
- Detects faces inside YOLO person bounding boxes using **OpenCV Haar Cascade**
- Compares embeddings using **cosine similarity** (threshold: 0.55)
- Enrolled faces stored in `backend/models/known_faces.json`

### Raspberry Pi fallback
The service checks `DEEPFACE_AVAILABLE` at import time. If DeepFace is not installed:
- All detections return `status: "unavailable"`
- All person detections trigger alerts (same as before — no regression)
- No crashes, no errors logged

### API Endpoints added to main.py

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/faces/enroll` | Upload a face photo + name to authorize a person |
| `GET`  | `/api/faces` | List all enrolled person names |
| `DELETE` | `/api/faces/{name}` | Remove a person and all their embeddings |

All endpoints require JWT auth (`Authorization: Bearer <token>`).

### Detection response (updated)
`POST /api/intruder/detect` now returns a `"face"` object per detection:

```json
{
  "intruder_detected": true,
  "detection_count": 1,
  "intruder_count": 1,
  "detections": [
    {
      "class": "Human",
      "confidence": 0.91,
      "bbox": [x1, y1, x2, y2],
      "face": {
        "face_found": true,
        "recognized": false,
        "name": null,
        "similarity": 0.31,
        "status": "intruder"
      }
    }
  ],
  "alert_id": "alert-1234567890",
  "detector_type": "local"
}
```

### Face status meanings

| status | Alert triggered? | Meaning |
|--------|-----------------|---------|
| `authorized` | ❌ No | Recognized enrolled person |
| `intruder` | ✅ Yes | Face found, not recognized |
| `no_face` | ✅ Yes | Person detected but no visible face |
| `no_enrolled` | ✅ Yes | No faces enrolled yet |
| `unavailable` | ✅ Yes | Pi fallback mode (DeepFace not installed) |

---

## How to Enroll Authorized Faces (Quick Steps)

```powershell
# 1. Get auth token
$resp = Invoke-RestMethod -Method POST http://127.0.0.1:8000/api/login `
  -ContentType "application/json" `
  -Body '{"email":"your@email.com","password":"yourpassword"}'
$token = $resp.token

# 2. Enroll a person (run multiple times with different photos for accuracy)
curl -X POST http://127.0.0.1:8000/api/faces/enroll `
  -H "Authorization: Bearer $token" `
  -F "name=John" `
  -F "file=@C:\path\to\john_face.jpg"

# 3. Verify
curl http://127.0.0.1:8000/api/faces -H "Authorization: Bearer $token"

# 4. Test detection
curl -X POST http://127.0.0.1:8000/api/intruder/detect `
  -H "Authorization: Bearer $token" `
  -F "file=@C:\path\to\test_image.jpg"
```

Tips:
- Upload **3–5 different photos** per person (different angles, lighting) for best accuracy
- Photos should clearly show the face (not from behind, not too small)
- Embeddings persist across backend restarts in `known_faces.json`

---

## Switching Between PC and Raspberry Pi

### PC (full mode — face recognition enabled)
```powershell
conda activate sensegrid
$env:DETECTOR_TYPE = "local"
python -m uvicorn main:app --reload --port 8000
```

### Raspberry Pi (fallback mode — YOLO only, no face recognition)
```bash
export DETECTOR_TYPE=local
python -m uvicorn main:app --host 0.0.0.0 --port 8000
# DeepFace not installed → auto-falls back, all humans trigger alerts
# No code changes needed — same codebase works on both
```

### To switch back to PC and preserve enrolled faces
The `backend/models/known_faces.json` file stores all enrolled faces. Copy it to your new machine to keep enrollments:
```powershell
# Copy from Pi to PC
scp pi@raspberrypi.local:/path/to/SenseGrid/backend/models/known_faces.json \
    i:\Web\Academic\SenseGrid\backend\models\
```

---

## What Still Needs to Be Done

- [ ] **Train YOLO model** — Run `model.ipynb` in Google Colab, download `best.pt` to `backend/models/`
- [ ] **Enroll authorized faces** — Start backend, use `/api/faces/enroll` endpoint
- [ ] **Test end-to-end** — Connect Pi, send a frame, verify alert only fires for unknown people
- [ ] **Frontend face status UI** — Currently the React dashboard shows alerts but doesn't show who was recognized. Could add a "Recognized: John" badge in `IntruderModal.jsx`
- [ ] **Tune similarity threshold** — Default is 0.55. If getting false positives, increase to 0.65. If not recognizing enrolled people, decrease to 0.45. Edit `SIMILARITY_THRESHOLD` in `face_recognizer.py`
- [ ] **Copy `known_faces.json` to Pi** if you want to run backend on Pi
- [ ] **Implement Pi-native lightweight face recognition** — see section below

---

## Raspberry Pi Native Face Recognition (NOT YET IMPLEMENTED)

> Current state: Pi falls back to YOLO-only mode (all humans trigger alerts). This section documents exactly what to build when you want real face recognition running on the Pi itself.

### Why DeepFace doesn't work on Pi
- ArcFace model = ~250MB, requires TensorFlow = ~1.5GB RAM
- Pi 4 has 4–8GB RAM but TF is very slow without GPU
- Pi Zero / Pi 3 would OOM completely

### Chosen approach: Haar Cascade + MobileFaceNet TFLite

| Component | Tool | Size | Purpose |
|-----------|------|------|---------|
| Face detection | OpenCV Haar Cascade | ~1MB, built-in | Find face region in person crop |
| Face embedding | MobileFaceNet (TFLite INT8) | ~1MB | Generate 128-dim face vector |
| Similarity | Cosine similarity (numpy) | 0 | Compare against enrolled embeddings |

MobileFaceNet is a purpose-built tiny face recognition model. Same idea as ArcFace but runs in ~30ms on Pi 4.

### Step 1 — Download the MobileFaceNet TFLite model

Download from Google MediaPipe or convert yourself:
- URL: https://storage.googleapis.com/mediapipe-models/face_embedder/face_embedder/float16/latest/face_embedder.tflite
- OR use the quantized INT8 version from: https://github.com/sirius-ai/MobileFaceNet_TF (export yourself)
- Save to: `backend/models/mobilefacenet.tflite`

### Step 2 — Create `backend/services/lightweight_face_recognizer.py` (NEW FILE)

This file does NOT exist yet. Create it with this structure:

```python
"""
Lightweight Face Recognizer for Raspberry Pi.

Uses:
- OpenCV Haar Cascade → face detection in person crop
- MobileFaceNet TFLite → 128-dim face embeddings (~1MB model)
- Cosine similarity → compare against known_faces.json

Same interface as FaceRecognizer in face_recognizer.py so they are
interchangeable — just swap which class get_face_recognizer() returns.
"""
import json
import numpy as np
import cv2
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
KNOWN_FACES_PATH = BACKEND_DIR / "models" / "known_faces.json"
MODEL_PATH = BACKEND_DIR / "models" / "mobilefacenet.tflite"
SIMILARITY_THRESHOLD = 0.55
MIN_FACE_SIZE = 40

class LightweightFaceRecognizer:
    def __init__(self):
        self._interpreter = None  # tflite.Interpreter, lazy-loaded
        self._known_faces = None

    def is_available(self) -> bool:
        return MODEL_PATH.exists()

    def _ensure_initialized(self):
        if self._interpreter is not None:
            return
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            import tensorflow.lite as tflite  # fallback if tflite_runtime not installed
        self._interpreter = tflite.Interpreter(model_path=str(MODEL_PATH))
        self._interpreter.allocate_tensors()

    def _get_embedding(self, face_img: np.ndarray) -> list:
        """Resize face to 112x112, run through MobileFaceNet, return 128-dim embedding."""
        self._ensure_initialized()
        face_resized = cv2.resize(face_img, (112, 112))
        face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
        face_norm = (face_rgb.astype(np.float32) - 127.5) / 128.0
        input_data = np.expand_dims(face_norm, axis=0)
        input_details = self._interpreter.get_input_details()
        output_details = self._interpreter.get_output_details()
        self._interpreter.set_tensor(input_details[0]['index'], input_data)
        self._interpreter.invoke()
        embedding = self._interpreter.get_tensor(output_details[0]['index'])[0]
        return embedding.tolist()

    # enroll_face(), recognize_face(), detect_and_recognize_faces(),
    # has_enrolled_faces(), get_enrolled_persons(), delete_person()
    # → implement with same signatures as FaceRecognizer in face_recognizer.py
    # → cosine similarity logic is identical, just _get_embedding() differs
```

### Step 3 — Update `get_face_recognizer()` in `face_recognizer.py`

Replace the singleton function at the bottom of `face_recognizer.py`:

```python
# CURRENT (only DeepFace):
def get_face_recognizer():
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = FaceRecognizer()
    return _recognizer_instance

# REPLACE WITH (auto-selects based on env var + availability):
def get_face_recognizer():
    global _recognizer_instance
    if _recognizer_instance is not None:
        return _recognizer_instance

    backend = os.getenv("FACE_RECOGNITION_BACKEND", "auto").lower()

    if backend == "deepface" or (backend == "auto" and DEEPFACE_AVAILABLE):
        _recognizer_instance = FaceRecognizer()
    elif backend == "lightweight" or backend == "pi":
        from .lightweight_face_recognizer import LightweightFaceRecognizer
        _recognizer_instance = LightweightFaceRecognizer()
    elif backend == "auto":
        # auto: try lightweight if model file exists, else fall back
        from pathlib import Path
        lite_model = Path(__file__).resolve().parent.parent / "models" / "mobilefacenet.tflite"
        if lite_model.exists():
            from .lightweight_face_recognizer import LightweightFaceRecognizer
            _recognizer_instance = LightweightFaceRecognizer()
        else:
            _recognizer_instance = FaceRecognizer()  # will raise if deepface missing
    else:
        _recognizer_instance = FaceRecognizer()

    return _recognizer_instance
```

### Step 4 — Update `backend/requirements.txt`

Add to the Pi section:
```
# Pi-native face recognition (alternative to deepface)
# tflite-runtime   ← install on Pi: pip install tflite-runtime
# numpy            ← already required
# opencv-python    ← already required
```

### Step 5 — Install on Pi

```bash
# On Raspberry Pi OS:
pip install tflite-runtime   # tiny, ~2MB, no TensorFlow needed
# opencv-python is already required by YOLO detection

# Download model
wget -O backend/models/mobilefacenet.tflite \
  https://storage.googleapis.com/mediapipe-models/face_embedder/face_embedder/float16/latest/face_embedder.tflite
```

### Step 6 — Set env var on Pi

```bash
export FACE_RECOGNITION_BACKEND=pi
# OR just drop mobilefacenet.tflite in backend/models/ and use BACKEND=auto
```

### Important: Embeddings are NOT compatible between backends

ArcFace (DeepFace) produces 512-dim vectors. MobileFaceNet produces 128-dim vectors. These are completely different spaces — you **cannot** enroll faces on your PC with DeepFace and then use the same `known_faces.json` on Pi with MobileFaceNet.

**Solution when you switch to Pi:**
1. Delete or rename `backend/models/known_faces.json`
2. Re-enroll all faces using the Pi backend
3. The enrollment API (`POST /api/faces/enroll`) is the same — only the embedding model underneath changes

### Files to touch (summary)

| File | Change needed |
|------|--------------|
| `backend/services/lightweight_face_recognizer.py` | **Create** (new file, full implementation) |
| `backend/services/face_recognizer.py` | Replace `get_face_recognizer()` with factory function above |
| `backend/models/mobilefacenet.tflite` | **Download** MobileFaceNet TFLite model |
| `backend/requirements.txt` | Add `tflite-runtime` comment for Pi |
| `backend/models/known_faces.json` | Delete and re-enroll when switching backends |

---

## Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DETECTOR_TYPE` | `roboflow` | `local` = YOLO (needs best.pt), `roboflow` = cloud API |
| `JWT_SECRET` | `dev-secret-key-...` | Change in production |
| `CORS_ORIGINS` | localhost:5173,5174 | Comma-separated allowed origins |

---

## Packages Changed / Added

| Package | Version | Note |
|---------|---------|------|
| `deepface` | 0.0.96 | Face recognition (server only) |
| `tf-keras` | 2.20.1 | TensorFlow backend for ArcFace |
| `opencv-python` | 4.10.0 | Image processing |
| `ultralytics` | 8.4.19 | YOLO inference |

> The `venv` conda environment was **not changed** — the above are only in `sensegrid`.
