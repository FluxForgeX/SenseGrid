#!/usr/bin/env python
"""
Webcam Intruder Detection Runner

Standalone script to run webcam-based intruder detection.
Works on Windows and Raspberry Pi.

Usage:
    python webcam_runner.py                    # Run without preview
    python webcam_runner.py --preview          # Run with live preview window
    python webcam_runner.py --interval 3       # Capture every 3 seconds
    python webcam_runner.py --cooldown 30      # 30 second alert cooldown
"""

import argparse
import signal
import sys
import time
import cv2

from services.webcam_service import WebcamService, WebcamConfig, draw_detections


def parse_args():
    parser = argparse.ArgumentParser(description="Webcam Intruder Detection")
    parser.add_argument("--preview", action="store_true", help="Show live preview window")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--interval", type=float, default=5.0, help="Capture interval in seconds")
    parser.add_argument("--cooldown", type=float, default=60.0, help="Alert cooldown in seconds")
    parser.add_argument("--confidence", type=float, default=0.5, help="Detection confidence threshold")
    parser.add_argument("--detector", type=str, default="roboflow", choices=["roboflow", "local"], 
                        help="Detector type")
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 60)
    print("SenseGrid Webcam Intruder Detection")
    print("=" * 60)
    print(f"  Camera Index: {args.camera}")
    print(f"  Capture Interval: {args.interval}s")
    print(f"  Alert Cooldown: {args.cooldown}s")
    print(f"  Confidence: {args.confidence}")
    print(f"  Detector: {args.detector}")
    print(f"  Preview: {'Enabled' if args.preview else 'Disabled'}")
    print("=" * 60)
    print()
    print("Press CTRL+C to stop")
    print()
    
    # Create config
    config = WebcamConfig(
        camera_index=args.camera,
        capture_interval=args.interval,
        alert_cooldown=args.cooldown,
        confidence_threshold=args.confidence,
        detector_type=args.detector,
        target_classes=["Human"],  # Only alert on humans
    )
    
    # Create service
    service = WebcamService(config=config)
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n[runner] Shutting down...")
        service.stop()
        if args.preview:
            cv2.destroyAllWindows()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start service
    if not service.start():
        print("[runner] Failed to start service")
        sys.exit(1)
    
    # Main loop
    try:
        if args.preview:
            print("[runner] Preview window opened. Press 'q' to quit.")
            while service.is_running:
                frame, detections = service.get_latest_frame()
                
                if frame is not None:
                    # Draw detections
                    frame = draw_detections(frame, detections, config.target_classes)
                    
                    # Add stats overlay
                    stats = service.get_stats()
                    cv2.putText(frame, f"Frames: {stats['frame_count']} | Alerts: {stats['detection_count']}", 
                                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    cv2.imshow("SenseGrid Intruder Detection", frame)
                
                # Check for quit key
                if cv2.waitKey(100) & 0xFF == ord('q'):
                    break
            
            cv2.destroyAllWindows()
        else:
            # No preview - just wait
            while service.is_running:
                time.sleep(1)
                
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        print("[runner] Done.")


if __name__ == "__main__":
    main()
