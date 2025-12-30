"""
Quick test script for local Roboflow inference server.
Tests detection using webcam capture.
"""
import cv2
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Testing Local Roboflow Inference Server")
print("=" * 60)
print(f"ROBOFLOW_LOCAL: {os.getenv('ROBOFLOW_LOCAL')}")
print(f"ROBOFLOW_LOCAL_URL: {os.getenv('ROBOFLOW_LOCAL_URL')}")
print(f"ROBOFLOW_WORKFLOW_ID: {os.getenv('ROBOFLOW_WORKFLOW_ID')}")
print("=" * 60)

# Test 1: Initialize detector
print("\n[1] Initializing detector...")
from services.roboflow_detector import get_roboflow_detector
detector = get_roboflow_detector()
print("✅ Detector initialized successfully!")

# Test 2: Capture frame from webcam
print("\n[2] Capturing frame from webcam...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Could not open webcam!")
    sys.exit(1)

ret, frame = cap.read()
cap.release()

if not ret:
    print("❌ Could not capture frame!")
    sys.exit(1)

# Save frame for testing
test_image_path = "test_webcam_frame.jpg"
cv2.imwrite(test_image_path, frame)
print(f"✅ Captured and saved frame to {test_image_path}")

# Test 3: Run detection
print("\n[3] Running detection on captured frame...")
try:
    detections = detector.detect(test_image_path)
    print(f"✅ Detection complete!")
    print(f"\n{'=' * 60}")
    print(f"RESULTS: Found {len(detections)} detection(s)")
    print(f"{'=' * 60}")
    
    for i, det in enumerate(detections):
        print(f"\n  Detection {i+1}:")
        print(f"    Class: {det.get('class')}")
        print(f"    Confidence: {det.get('confidence', 0):.2%}")
        print(f"    BBox: {det.get('bbox')}")
    
    if len(detections) == 0:
        print("\n  No humans/intruders detected in frame.")
        print("  Try positioning yourself in front of the camera!")
    
except Exception as e:
    print(f"❌ Detection failed: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
if os.path.exists(test_image_path):
    os.remove(test_image_path)
    print(f"\n[Cleanup] Removed {test_image_path}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
