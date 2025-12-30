"""
Local webcam test for intruder detection.
Used only for development on Windows laptop.

This script opens your webcam and runs real-time intruder detection
using the trained YOLO model (best.pt).

Usage:
    python services/webcam_test.py

Controls:
    - Press 'q' to quit
    - Green boxes appear around detected humans
    - Console prints alerts with cooldown

Requirements:
    - Webcam must be accessible (usually index 0)
    - best.pt model must be in backend/models/
"""

from intruder_detector import get_detector
import cv2
import time


def main():
    """
    Run real-time intruder detection on webcam feed.
    """
    # Initialize detector
    try:
        detector = get_detector()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n📍 Please ensure best.pt is located at: backend/models/best.pt")
        return
    
    # Open webcam (index 0 = default camera)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Webcam not accessible")
        print("   Make sure no other application is using the camera")
        return
    
    # Set camera resolution (optional, for better performance)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("✅ Webcam running. Press 'q' to quit.")
    print("=" * 50)
    
    # Alert cooldown to avoid spam
    last_alert_time = 0
    COOLDOWN = 10  # seconds between alerts
    
    # FPS counter
    fps_start_time = time.time()
    fps_frame_count = 0
    fps = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break
        
        # Run detection on current frame
        detections = detector.detect_from_frame(frame, conf=0.5, iou=0.35)
        
        human_detected = False
        
        # Draw bounding boxes on frame
        for detection in detections:
            human_detected = True
            
            # Extract bbox coordinates
            x1, y1, x2, y2 = map(int, detection["bbox"])
            confidence = detection["confidence"]
            
            # Draw green rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label with confidence
            label = f"Human {confidence:.2f}"
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
        
        # Print alert with cooldown
        now = time.time()
        if human_detected and now - last_alert_time > COOLDOWN:
            print(f"🚨 Intruder detected at {time.strftime('%H:%M:%S')}")
            print(f"   Confidence: {detections[0]['confidence']:.2%}")
            last_alert_time = now
        
        # Calculate FPS
        fps_frame_count += 1
        if now - fps_start_time >= 1.0:
            fps = fps_frame_count / (now - fps_start_time)
            fps_frame_count = 0
            fps_start_time = now
        
        # Display FPS on frame
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )
        
        # Display detection count
        if detections:
            status_text = f"DETECTED: {len(detections)} human(s)"
            color = (0, 0, 255)  # Red
        else:
            status_text = "NO DETECTION"
            color = (0, 255, 0)  # Green
        
        cv2.putText(
            frame,
            status_text,
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )
        
        # Show frame
        cv2.imshow("SenseGrid Intruder Detection Test", frame)
        
        # Check for 'q' key press
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n👋 Exiting...")
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Webcam test completed")


if __name__ == "__main__":
    main()
