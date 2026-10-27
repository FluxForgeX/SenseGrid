# 🚀 SenseGrid — Complete Setup & Run Guide (Windows & Cross-Platform)

Welcome to **SenseGrid**! This guide will walk you through setting up and running the complete project (Backend, Frontend, YOLO Intruder Detection, and Face Recognition) on **Windows** after a fresh clone.

---

## ⚡ Quick Start (1-Click Launch on Windows)

If you already have Python (3.9–3.11) and Node.js installed, you can use the pre-configured 1-click launchers in the project root:

| Script | Purpose |
|---|---|
| **[`run_all.bat`](file:///e:/Al%20Amin/SenseGrid/run_all.bat)** | Launches both Backend (`:8000`) and Frontend (`:5173`) in separate windows |
| **[`run_webcam.bat`](file:///e:/Al%20Amin/SenseGrid/run_webcam.bat)** | Opens the live OpenCV GUI webcam with YOLO intruder detection and full post-run analysis report |
| **[`enroll_face.bat`](file:///e:/Al%20Amin/SenseGrid/enroll_face.bat)** | Enrolls your face with your name so you are detected as **Authorized** (not an intruder) |
| **[`run_backend.bat`](file:///e:/Al%20Amin/SenseGrid/run_backend.bat)** | Starts only the FastAPI backend server |
| **[`run_frontend.bat`](file:///e:/Al%20Amin/SenseGrid/run_frontend.bat)** | Starts only the Vite frontend dev server |

---

## 🛠️ Step-by-Step Setup from a Fresh Clone

### Prerequisites
- **Python**: Version 3.10 is recommended (3.9 to 3.11 supported).
- **Node.js**: v18+ with `npm`.
- **Webcam**: Laptop built-in webcam or USB camera.

---

### Step 1: Configure Environment Variables

#### 1. Backend `.env`
In `backend/`, copy `.env.example` to `.env`:
```powershell
cd backend
Copy-Item .env.example .env
```
Ensure your `backend/.env` has a valid JWT secret and local settings:
```ini
PORT=8000
HOST=127.0.0.1
JWT_SECRET=029436a103e51c6975f1e74d433b3e58138326f9476a52ca6b5c6db7eb0965df
DATABASE_URL=sqlite:///./sensegrid.db
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174
DETECTOR_TYPE=local
WEBCAM_CAMERA_INDEX=0
WEBCAM_CAPTURE_INTERVAL=2.0
```

#### 2. Frontend `.env`
In `frontend/`, copy `.env.example` to `.env`:
```powershell
cd ..\frontend
Copy-Item .env.example .env
```
Ensure your `frontend/.env` contains:
```ini
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=http://localhost:8000
VITE_APP_NAME=SenseGrid
VITE_APP_VERSION=1.0.0
```

---

### Step 2: Set Up Backend Python Environment

From the project root:
```powershell
cd backend

# 1. Create a virtual environment using Python 3.10:
py -3.10 -m venv .venv
# (or: python -m venv .venv)

# 2. Activate the virtual environment:
.\.venv\Scripts\Activate.ps1
# (or in CMD: .\.venv\Scripts\activate.bat)

# 3. Upgrade pip:
python -m pip install --upgrade pip

# 4. Install dependencies:
pip install -r requirements.txt

# 5. Initialize the database:
python -c "from database import init_db; init_db(); print('✓ Database initialized successfully')"
```

---

### Step 3: Copy Pre-Trained YOLO Models

Copy the trained models from the `weights/` directory into `backend/models/`:
```powershell
cd ..
Copy-Item "weights\best.pt" -Destination "backend\models\best.pt"
Copy-Item "weights\best.onnx" -Destination "backend\models\best.onnx"
```

---

### Step 4: Install Frontend Dependencies

```powershell
cd frontend
npm install
```

---

## 🎯 Running SenseGrid

### Option A: 1-Click Launch (Recommended)
Simply double-click:
```powershell
.\run_all.bat
```
This automatically starts:
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Frontend PWA**: [http://localhost:5173](http://localhost:5173)

---

### Option B: Run in Separate Terminals

#### Terminal 1 (Backend):
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

#### Terminal 2 (Frontend):
```powershell
cd frontend
npm run dev
```

---

## 👁️ Live Webcam Intruder Detection & Accuracy Analysis

To test your AI model with live webcam detection and real-time bounding boxes:

```powershell
# Run for 60 seconds with 2.0s detection interval:
.\run_webcam.bat --duration 60 --interval 2.0

# Run indefinitely until you press 'q':
.\run_webcam.bat --duration 0

# Run for 30 seconds:
.\run_webcam.bat --duration 30
```

### Live Controls in the Webcam Window:
- <kbd>Q</kbd> or <kbd>ESC</kbd>: Exit preview and generate accuracy report.
- <kbd>S</kbd>: Save high-resolution snapshot to `backend/snapshots/`.
- <kbd>+</kbd> / <kbd>-</kbd>: Increase / decrease detection confidence threshold.

### Automatic Post-Run Calculation & Analysis Report
When the session ends, a complete analysis report is printed in your terminal:
- **Accuracy Metrics**: Precision, Recall, Accuracy, and F1-Score.
- **Confusion Matrix**: True Positives (TP), False Positives (FP), True Negatives (TN), False Negatives (FN).
- **Detection Breakdown**: Total Humans detected, Authorized Persons recognized, Intruder Alerts triggered, and Animals detected.
- **Confidence Statistics**: Average, Minimum, and Maximum confidence scores.

---

## 👤 Face Recognition (How to Be Detected as Authorized)

In SenseGrid, recognized faces are treated as **Authorized** and do **NOT** trigger intruder alarms.

### 1. Enroll Your Face (Takes 5 seconds):
```powershell
.\enroll_face.bat "YourName"
```
```powershell
# Standard 3-angle enrollment (Center, Left, Right):
.\enroll_face.bat "YourName"

# Hands-free auto-capture with 3-second countdown:
.\enroll_face.bat "YourName" --auto

# For glasses wearers (guided 4 angles: 2 with glasses, 2 without glasses):
.\enroll_face.bat "YourName" --glasses

# Both hands-free AND with/without glasses:
.\enroll_face.bat "YourName" --glasses --auto
```

1. Look at your camera.
2. In manual mode, press <kbd>SPACE</kbd> to capture each angle (or press <kbd>G</kbd> to toggle Glasses Mode).
3. In `--glasses` mode, it guides you through **Step 1 (Glasses ON)** and **Step 2 (REMOVE Glasses)**.
4. Your face embeddings are stored in `backend/models/known_faces.json`.

### 2. Verify:
Run `.\run_webcam.bat --duration 60 --interval 2.0`. Your name and similarity score (e.g. `YourName (0.68) 0.85`) will now be displayed in bright green above your face whether you are wearing glasses or not, and you will never be falsely flagged as an intruder!

---

## 🔧 Windows Troubleshooting

### 1. "cv2.error: (-2:Unspecified error) The function is not implemented"
- **Cause**: A headless OpenCV build (`opencv-contrib-python-headless`) was installed.
- **Fix**: Run in the backend virtual environment:
  ```powershell
  cd backend
  .\.venv\Scripts\Activate.ps1
  pip uninstall -y opencv-contrib-python-headless opencv-python-headless
  pip install --force-reinstall opencv-python==4.10.0.84
  ```

### 2. PowerShell Script Execution Disabled (`cannot be loaded because running scripts is disabled`)
- **Fix**: Run once in your PowerShell terminal:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 3. Port Already in Use (Port 8000 or 5173)
- Check what is holding port 8000:
  ```powershell
  netstat -ano | findstr :8000
  ```
- Or run on a different port:
  ```powershell
  python -m uvicorn main:app --reload --port 8001
  ```
