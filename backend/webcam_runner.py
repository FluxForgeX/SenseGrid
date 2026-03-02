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


def print_accuracy_report(stats: dict):
    frames   = stats["frame_count"]
    caught   = stats["frames_with_detection"]
    alerts   = stats["detection_count"]
    accuracy = stats["accuracy"]
    elapsed  = stats["elapsed_seconds"]

    print()
    print("=" * 60)
    print("  ACCURACY REPORT")
    print("=" * 60)
    print(f"  Duration        : {elapsed:.1f}s")
    print(f"  Frames Analyzed : {frames}")
    print(f"  Humans Caught   : {caught}  (frames with detection)")
    print(f"  Alerts Fired    : {alerts}")
    print(f"  Detection Rate  : {accuracy:.1f}%")
    print("=" * 60)
    print()


def parse_args():
    parser = argparse.ArgumentParser(description="Webcam Intruder Detection")
    parser.add_argument("--preview", action="store_true", help="Show live preview window")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--interval", type=float, default=2.0, help="Detection interval in seconds (default: 2.0)")
    parser.add_argument("--cooldown", type=float, default=60.0, help="Alert cooldown in seconds")
    parser.add_argument("--confidence", type=float, default=0.35, help="Detection confidence threshold (default: 0.35)")
    parser.add_argument("--detector", type=str, default="roboflow", choices=["roboflow", "local"], 
                        help="Detector type")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Run for this many seconds then print accuracy report (0 = run forever)")
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
    print(f"  Duration: {'Forever' if args.duration == 0 else f'{args.duration}s (accuracy report at end)'}")
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
        print_accuracy_report(service.get_stats())
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
        run_start = time.time()

        if args.preview:
            print("[runner] Preview window opened. Press 'q' to quit.")
            while service.is_running:
                # Auto-stop after duration
                if args.duration > 0 and (time.time() - run_start) >= args.duration:
                    print(f"\n[runner] ⏱ {args.duration:.0f}s elapsed — stopping for accuracy report...")
                    break

                frame, detections = service.get_latest_frame()
                
                if frame is not None:
                    # Draw detections
                    frame = draw_detections(frame, detections, config.target_classes)
                    
                    # Add stats overlay
                    stats = service.get_stats()
                    elapsed = stats["elapsed_seconds"]
                    accuracy = stats["accuracy"]
                    caught   = stats["frames_with_detection"]
                    frames   = stats["frame_count"]
                    alerts   = stats["detection_count"]

                    # Time remaining bar
                    if args.duration > 0:
                        remaining = max(0, args.duration - (time.time() - run_start))
                        timer_text = f"Time: {remaining:.0f}s left"
                    else:
                        timer_text = f"Time: {elapsed:.0f}s"

                    overlay_lines = [
                        f"Frames: {frames}  Caught: {caught}  Alerts: {alerts}  FPS: {stats.get('fps', 0.0):.0f}",
                        f"Detection Rate: {accuracy:.1f}%   {timer_text}",
                    ]
                    for i, line in enumerate(overlay_lines):
                        y = 25 + i * 28
                        cv2.putText(frame, line, (10, y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3)
                        cv2.putText(frame, line, (10, y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                    
                    cv2.imshow("SenseGrid Intruder Detection", frame)
                
                # Check for quit key (~30fps, non-blocking)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cv2.destroyAllWindows()
        else:
            # No preview - just wait
            while service.is_running:
                if args.duration > 0 and (time.time() - run_start) >= args.duration:
                    print(f"\n[runner] ⏱ {args.duration:.0f}s elapsed — stopping for accuracy report...")
                    break
                time.sleep(1)
                
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        print_accuracy_report(service.get_stats())
        print("[runner] Done.")


if __name__ == "__main__":
    main()
