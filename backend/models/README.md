# Models Directory

This directory is for **local YOLO models only** (alternative detection method).

## 🌐 Primary Detection Method: Roboflow Cloud API

**You DO NOT need to place any model files here if using Roboflow (default).**

The default configuration uses Roboflow's serverless inference API, which:
- ✅ Requires NO local model files
- ✅ Works on Windows and Raspberry Pi (with internet)
- ✅ Provides automatic scaling and updates
- ✅ Reduces memory footprint

**Setup for Roboflow:**
1. Get API credentials from https://app.roboflow.com
2. Configure in `backend/.env`:
   ```bash
   ROBOFLOW_API_KEY=your_key_here
   ROBOFLOW_WORKSPACE=project-ark
   ROBOFLOW_WORKFLOW_ID=custom-workflow-2
   DETECTOR_TYPE=roboflow
   ```
3. Install: `pip install inference-sdk`
4. Done! No model files needed.

---

## 🔌 Alternative: Local YOLO Detection (Offline)

If you want **offline detection** without internet dependency:

### Step 1: Place Model File

Copy your trained YOLO model to this directory:

```bash
backend/models/best.pt
```

The file MUST be named `best.pt` exactly.

### Step 2: Configure Environment

Edit `backend/.env`:

```bash
DETECTOR_TYPE=local
```

---

## 🍓 TFLite Detection (RECOMMENDED for Raspberry Pi)

Optimized for ARM processors with INT8 quantized models (~3MB, fastest inference).

### Step 1: Place Model File

Copy the INT8 quantized model:

```bash
backend/models/best_int8.tflite
```

Alternatively, set a custom path via environment variable:
```bash
DETECTOR_MODEL_PATH=/path/to/your/model.tflite
```

### Step 2: Configure Environment

Edit `backend/.env`:

```bash
DETECTOR_TYPE=tflite
# Optional: custom model path
# DETECTOR_MODEL_PATH=/path/to/model.tflite
# Optional: confidence threshold (default 0.5)
# DETECTOR_CONFIDENCE=0.5
```

### Step 3: Install Dependencies

For Raspberry Pi (lightweight runtime):
```bash
pip install tflite-runtime numpy opencv-python
```

For desktop (full TensorFlow as fallback):
```bash
pip install tensorflow numpy opencv-python
```

### Step 4: Restart Backend

```powershell
python -m uvicorn main:app --reload
```

**Expected log:**
```
✅ TFLite detector loaded: best_int8.tflite
   Input shape: [1, 416, 416, 3], dtype: <class 'numpy.int8'>
   Quantized: True
```

### Available TFLite Models

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `best_int8.tflite` | ~3 MB | Fastest | Good | **Raspberry Pi (recommended)** |
| `best_float16.tflite` | ~6 MB | Fast | Better | GPU acceleration |
| `best_float32.tflite` | ~12 MB | Slower | Best | Maximum accuracy |

### Step 3: Install Dependencies

Uncomment these lines in `backend/requirements.txt`:
```
# ultralytics
# opencv-python
```

Then install:
```powershell
pip install ultralytics opencv-python
```

### Step 4: Restart Backend

```powershell
python -m uvicorn main:app --reload
```

**Expected log:**
```
✅ Local YOLO detector loaded from d:\...\backend\models\best.pt
```

---

## 📊 Comparison

| Feature | Roboflow Cloud | Local YOLO | TFLite (Pi) |
|---------|---------------|------------|-------------|
| **Internet Required** | Yes | No | No |
| **Model File Needed** | No | Yes (best.pt) | Yes (best_int8.tflite) |
| **Setup Complexity** | Easy | Medium | Easy |
| **Memory Usage** | Low (~30 MB) | High (~300 MB) | Very Low (~50 MB) |
| **Inference Speed** | ~200-500ms | ~100-300ms | ~200-400ms (Pi) |
| **Model Updates** | Instant (dashboard) | Manual | Manual |
| **Privacy** | Data sent to Roboflow | Local | Local |
| **Best For** | Desktop/Cloud | Desktop+GPU | **Raspberry Pi** |

---

## 🔄 Switching Between Methods

The system uses a **factory pattern** to switch detectors without code changes:

**In `.env`:**
```bash
# Use Roboflow Cloud API (desktop, requires internet)
DETECTOR_TYPE=roboflow

# OR use local YOLO model (desktop with GPU)
DETECTOR_TYPE=local

# OR use TFLite (Raspberry Pi, recommended)
DETECTOR_TYPE=tflite
```

**Optional:** Set custom model path:
```bash
DETECTOR_MODEL_PATH=/path/to/your/model.tflite
```

No other code changes required - just restart the backend!

---

## ✅ Verification

### Roboflow (no files here)
```powershell
# Should show empty or just this README
dir backend\models
```

### Local YOLO
```powershell
# Should show best.pt file
dir backend\models\best.pt
# File size: typically 10-100 MB
```

---

## 📚 More Information

- Full setup: [INTRUDER_DETECTION_SETUP.md](../../INTRUDER_DETECTION_SETUP.md)
- Quick start: [QUICK_START_INTRUDER_DETECTION.md](../../QUICK_START_INTRUDER_DETECTION.md)
- Integration details: [INTEGRATION_SUMMARY.md](../../INTEGRATION_SUMMARY.md)

---

**TL;DR:**
- **Default (Roboflow):** No files needed here ✅
- **Alternative (Local YOLO):** Place `best.pt` here + set `DETECTOR_TYPE=local`
- **Raspberry Pi (TFLite):** Place `best_int8.tflite` here + set `DETECTOR_TYPE=tflite` ✅
