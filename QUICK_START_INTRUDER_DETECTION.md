# 🚀 Quick Start Guide - Roboflow Cloud Intruder Detection

**Complete this in 3 minutes!**

---

## ✅ Step 1: Get Roboflow Credentials (1 minute)

1. Go to https://app.roboflow.com
2. Copy your **API Key** from Settings
3. Note your **Workspace Name** (e.g., "project-ark")
4. Note your **Workflow ID** (e.g., "custom-workflow-2")

---

## ✅ Step 2: Configure Environment (30 seconds)

Edit `backend/.env` (create from `.env.example` if needed):

```bash
ROBOFLOW_API_KEY=your_api_key_here
ROBOFLOW_WORKSPACE=project-ark
ROBOFLOW_WORKFLOW_ID=custom-workflow-2
DETECTOR_TYPE=roboflow
```

**⚠️ Never commit `.env` to Git!**

---

## ✅ Step 3: Install Dependencies (1 minute)

```powershell
cd backend
.\.venv311\Scripts\activate
pip install -r requirements.txt
```

This installs `inference-sdk` (Roboflow API client).

---

## ✅ Step 4: Start Backend (30 seconds)

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Look for this line:**
```
✅ Roboflow detector initialized
   Workspace: project-ark
   Workflow: custom-workflow-2
```

---

## ✅ Step 5: Test API (30 seconds)

```powershell
# In new terminal
cd backend
python test_detection_api.py path\to\test-image.jpg
```

Enter your email/password when prompted.

---

## 🎉 You're Done!

Your backend now has:
- ✅ Roboflow Cloud API integration
- ✅ Image upload endpoint at `/api/intruder/detect`
- ✅ Alert creation when humans detected
- ✅ Socket.IO real-time notifications
- ✅ Works on Windows and Raspberry Pi (with internet)

---

## 📖 Full Documentation

See [INTRUDER_DETECTION_SETUP.md](INTRUDER_DETECTION_SETUP.md) for:
- Detailed configuration
- Switching to local YOLO model
- Frontend integration
- Troubleshooting

---

## 🔄 Want Offline Detection?

To use local YOLO model instead:

1. Place `best.pt` in `backend/models/`
2. Uncomment `ultralytics` and `opencv-python` in `requirements.txt`
3. Run `pip install ultralytics opencv-python`
4. Set `DETECTOR_TYPE=local` in `.env`
5. Restart backend

See full guide for details.

---

## ❓ Issues?

### API key errors
→ Check `.env` has correct `ROBOFLOW_API_KEY`
→ Verify credentials at https://app.roboflow.com

### Import errors
→ Run `pip install -r requirements.txt`
→ Make sure venv is activated

### Connection errors
→ Check internet connection
→ Verify Roboflow service is accessible

---

**Need help?** Check the full setup guide: [INTRUDER_DETECTION_SETUP.md](INTRUDER_DETECTION_SETUP.md)
