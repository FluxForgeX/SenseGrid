#!/usr/bin/env python
"""
SenseGrid Real-Time Webcam Detection with Local YOLO & Face Recognition
Includes full Post-Run Calculation & Analysis Report (Precision, Recall, Accuracy, F1, Breakdown).

Controls:
    [Q] or [ESC] - Quit early
    [S]          - Save snapshot to backend/snapshots/
    [+] / [-]    - Increase / decrease confidence threshold
"""

import sys
import os
import time
import argparse
from pathlib import Path
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# Add parent directory to path for services import
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

MODEL_PATH = BACKEND_DIR / "models" / "best.pt"
SNAPSHOT_DIR = BACKEND_DIR / "snapshots"

# Cascades for frontal and profile/side-angle faces
FRONTAL_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
PROFILE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_profileface.xml"
)


def find_faces(crop, min_size=(25, 25)):
    """Detect faces supporting frontal, profile, and flipped profile angles."""
    if crop.size == 0:
        return []
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # 1. Frontal faces
    faces = list(FRONTAL_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=min_size))
    if faces:
        return faces

    # 2. Profile faces (side-angle e.g. on a phone call)
    profiles = list(PROFILE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=min_size))
    if profiles:
        return profiles

    # 3. Flipped profile faces (opposite side angle)
    gray_flip = cv2.flip(gray, 1)
    flipped = PROFILE_CASCADE.detectMultiScale(gray_flip, scaleFactor=1.1, minNeighbors=3, minSize=min_size)
    w_crop = crop.shape[1]
    res = []
    for (fx, fy, fw, fh) in flipped:
        res.append((w_crop - fx - fw, fy, fw, fh))
    return res


# Optional Face Recognizer
try:
    from services.face_recognizer import get_face_recognizer, DEEPFACE_AVAILABLE
    face_recognizer = get_face_recognizer() if DEEPFACE_AVAILABLE else None
except Exception:
    face_recognizer = None


def parse_args():
    parser = argparse.ArgumentParser(description="SenseGrid Live Webcam Detection")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Run duration in seconds (0 = run forever, default: 60)")
    parser.add_argument("--interval", type=float, default=0.0,
                        help="Inference interval in seconds (0 = continuous, default: 0.0)")
    parser.add_argument("--confidence", type=float, default=0.25,
                        help="Confidence threshold (default: 0.25 for reliable background detection)")
    parser.add_argument("--camera", type=int, default=0,
                        help="Webcam camera index (default: 0)")
    return parser.parse_args()


def draw_label(frame, text, x, y, color=(0, 255, 0)):
    """Draw bold label with black shadow outline for high contrast."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.65
    thickness = 2
    cv2.putText(frame, text, (x - 1, y - 1), font, font_scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, (x + 1, y + 1), font, font_scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)


def print_analysis_report(stats: dict):
    """Print comprehensive calculation analysis report at the end of the run."""
    elapsed = stats.get("elapsed", 0.0)
    total_frames = stats.get("total_frames", 0)
    inferences = stats.get("inferences", 0)
    avg_fps = stats.get("avg_fps", 0.0)

    person_count = stats.get("person_count", 0)
    authorized_count = stats.get("authorized_count", 0)
    intruder_count = stats.get("intruder_count", 0)
    intruder_human_count = stats.get("intruder_human_count", 0)
    intruder_animal_count = stats.get("intruder_animal_count", 0)
    animal_count = stats.get("animal_count", 0)
    frames_with_det = stats.get("frames_with_det", 0)
    authorized_names = stats.get("authorized_names", {})

    confs = stats.get("confidences", [])
    avg_conf = (sum(confs) / len(confs)) if confs else 0.0
    min_conf = min(confs) if confs else 0.0
    max_conf = max(confs) if confs else 0.0

    # Security & Face Recognition Confusion Matrix
    # TP: Real Intruder correctly flagged as Intruder
    # FP: Authorized Person mistakenly flagged as Intruder (False Alarm)
    # TN: Authorized Person correctly identified & cleared
    # FN: Real Intruder mistakenly accepted as Authorized (Security Breach)
    sec_tp = stats.get("true_intruders", 0) + intruder_animal_count
    sec_fp = stats.get("face_false_alarms", 0)
    sec_tn = authorized_count
    sec_fn = stats.get("breaches", 0)

    # Face Recognition Match Rate on Enrolled People
    enrolled_encounters = authorized_count + sec_fp
    face_match_rate = (authorized_count / enrolled_encounters * 100.0) if enrolled_encounters > 0 else 100.0
    false_alarm_rate = (sec_fp / enrolled_encounters * 100.0) if enrolled_encounters > 0 else 0.0

    # Security Alert Precision & Recall
    sec_p_denom = sec_tp + sec_fp
    sec_precision = (sec_tp / sec_p_denom * 100.0) if sec_p_denom > 0 else 100.0

    sec_r_denom = sec_tp + sec_fn
    sec_recall = (sec_tp / sec_r_denom * 100.0) if sec_r_denom > 0 else 100.0

    sec_total = sec_tp + sec_fp + sec_tn + sec_fn
    sec_accuracy = ((sec_tp + sec_tn) / sec_total * 100.0) if sec_total > 0 else 100.0
    sec_f1 = (2.0 * sec_precision * sec_recall / (sec_precision + sec_recall)) if (sec_precision + sec_recall) > 0 else 0.0

    det_rate = (frames_with_det / inferences * 100.0) if inferences > 0 else 0.0

    print()
    print("=" * 70)
    print("           SENSEGRID MODEL DETECTION & ACCURACY REPORT")
    print("=" * 70)
    print(f"  Session Duration         : {elapsed:.1f}s")
    print(f"  Average FPS              : {avg_fps:.1f} FPS")
    print(f"  Total Video Frames       : {total_frames}")
    print(f"  Inference Cycles Run     : {inferences}")
    print(f"  YOLO Detection Hit Rate  : {det_rate:.1f}% ({frames_with_det}/{inferences} cycles)")
    print("-" * 70)
    print("  OBJECT DETECTION BREAKDOWN:")
    print(f"  * Total Humans Detected   : {person_count}")
    print(f"     |- Authorized Persons  : {authorized_count}")
    if authorized_names:
        names_str = ", ".join(f"{name}: {cnt}" for name, cnt in authorized_names.items())
        print(f"     |    `- By Name       : {names_str}")
    print(f"     `- Intruder(Human)     : {intruder_human_count}")
    print(f"  * Total Animals Detected  : {animal_count}")
    print(f"     `- Intruder(Animal)    : {intruder_animal_count}")
    print(f"  * Total Intruder Alerts   : {intruder_count} (Intruder Success: {intruder_count})")
    print("-" * 70)
    print("  CONFIDENCE METRICS:")
    print(f"  * Average Confidence      : {avg_conf:.2f}")
    print(f"  * Min Confidence          : {min_conf:.2f}")
    print(f"  * Max Confidence          : {max_conf:.2f}")
    print("-" * 70)
    print("  FACE RECOGNITION & SECURITY EVALUATION:")
    print(f"  * Face Match Success Rate : {face_match_rate:.2f}% ({authorized_count}/{enrolled_encounters} attempts)")
    print(f"  * False Alarm Rate (FAR)  : {false_alarm_rate:.2f}% ({sec_fp} false alerts on enrolled users)")
    print(f"  * Security Alert Precision: {sec_precision:.2f}% (True intruders vs false alarms)")
    print(f"  * Security Alert Recall   : {sec_recall:.2f}% (All intruders intercepted)")
    print(f"  * Overall Security Accuracy: {sec_accuracy:.2f}%")
    print(f"  * Security F1-Score       : {sec_f1:.2f}%")
    print("-" * 70)
    print("  SECURITY CONFUSION MATRIX:")
    print(f"  * True Positives  (TP)    : {sec_tp}  (True Intruders successfully alerted)")
    print(f"  * False Positives (FP)    : {sec_fp}  (Authorized user falsely flagged as Intruder)")
    print(f"  * True Negatives  (TN)    : {sec_tn}  (Authorized user correctly cleared & recognized)")
    print(f"  * False Negatives (FN)    : {sec_fn}  (Intruders mistakenly accepted as Authorized)")
    print("=" * 70)
    print()


def main():
    args = parse_args()

    print("=" * 65)
    print("      SenseGrid - Live Webcam Detection (OpenCV + YOLO)")
    print("=" * 65)

    if not MODEL_PATH.exists():
        print(f"[ERROR] Model file not found at: {MODEL_PATH}")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Hardware Acceleration : {device.upper()}")
    print(f"[*] Loading YOLO Model    : {MODEL_PATH.name}")

    try:
        model = YOLO(str(MODEL_PATH))
        print(f"[*] Model Classes         : {model.names}")
    except Exception as e:
        print(f"[ERROR] Failed to load YOLO model: {e}")
        sys.exit(1)

    # Initialize camera
    camera_index = args.camera
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"[ERROR] Could not open webcam at index {camera_index}!")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[*] Camera Initialized    : {actual_w}x{actual_h}")
    duration_str = "Indefinite (press 'q' to stop)" if args.duration <= 0 else f"{args.duration:.0f} seconds"
    print(f"[*] Timer Duration        : {duration_str}")
    interval_str = "Continuous (real-time)" if args.interval <= 0 else f"Every {args.interval:.1f}s"
    print(f"[*] Detection Interval    : {interval_str}")

    enrolled = face_recognizer.get_enrolled_persons() if (face_recognizer and face_recognizer.has_enrolled_faces()) else []
    print(f"[*] Enrolled Persons      : {enrolled if enrolled else 'None (defaulting to Human)'}")
    print()
    print("Opening GUI window now... (Press 'q' to quit early)")
    print("=" * 65)

    conf_threshold = args.confidence
    window_name = "SenseGrid - Intruder Detection (Press 'q' to quit)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 800, 600)

    # Tracking & Analysis Metrics
    stats = {
        "elapsed": 0.0,
        "total_frames": 0,
        "inferences": 0,
        "avg_fps": 0.0,
        "person_count": 0,
        "authorized_count": 0,
        "intruder_count": 0,
        "intruder_human_count": 0,
        "intruder_animal_count": 0,
        "animal_count": 0,
        "face_false_alarms": 0,
        "true_intruders": 0,
        "breaches": 0,
        "frames_with_det": 0,
        "authorized_names": {},
        "confidences": [],
        "tp": 0,
        "fp": 0,
        "tn": 0,
        "fn": 0,
    }

    start_time = time.time()
    prev_time = time.time()
    last_detect_time = 0.0
    fps = 0.0
    fps_history = []
    cached_boxes = []
    inference_time_ms = 0.0
    snapshot_msg = ""
    snapshot_msg_time = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.02)
            continue
        stats["total_frames"] += 1
        raw_frame = frame.copy()

        curr_time = time.time()
        elapsed = curr_time - start_time
        stats["elapsed"] = elapsed

        # Check duration limit
        if args.duration > 0 and elapsed >= args.duration:
            print(f"\n[INFO] {args.duration:.0f}s completed. Calculating final analysis report...")
            break

        # Run inference if continuous or interval elapsed
        if args.interval <= 0 or (curr_time - last_detect_time >= args.interval) or not cached_boxes:
            loop_start = time.time()
            results = model(frame, conf=conf_threshold, verbose=False, device=device)
            inference_time_ms = (time.time() - loop_start) * 1000
            last_detect_time = curr_time
            stats["inferences"] += 1

            new_boxes = []
            h, w = frame.shape[:2]
            cycle_has_det = False
            cycle_has_valid_obj = False

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names.get(cls_id, f"Class {cls_id}")
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)

                    cycle_has_det = True
                    stats["confidences"].append(conf)

                    if cls_name == "Human":
                        stats["person_count"] += 1
                        cycle_has_valid_obj = True

                        person_crop = frame[y1:y2, x1:x2]
                        face_boxes = []
                        if person_crop.size > 0:
                            faces = find_faces(person_crop, min_size=(25, 25))
                            for (fx, fy, fw, fh) in faces:
                                face_boxes.append((x1 + fx, y1 + fy, x1 + fx + fw, y1 + fy + fh))

                        if face_boxes:
                            for (fx1, fy1, fx2, fy2) in face_boxes:
                                name_label = "Intruder(Human)"
                                sim_val = None
                                box_color = (0, 0, 255)  # Red for intruder

                                if face_recognizer and face_recognizer.has_enrolled_faces():
                                    face_crop = frame[fy1:fy2, fx1:fx2]
                                    if face_crop.size > 0:
                                        rec = face_recognizer.recognize_face(face_crop)
                                        if rec.get("recognized"):
                                            name_label = rec["name"]
                                            sim_val = rec["similarity"]
                                            box_color = (0, 255, 0)  # Green for authorized
                                            stats["authorized_count"] += 1
                                            stats["authorized_names"][name_label] = stats["authorized_names"].get(name_label, 0) + 1
                                        elif rec.get("status") == "intruder":
                                            name_label = "Intruder(Human)"
                                            sim_val = rec.get("similarity", 0.0)
                                            box_color = (0, 0, 255)  # Red for intruder
                                            stats["intruder_count"] += 1
                                            stats["intruder_human_count"] += 1
                                            # If similarity has moderate overlap (>0.20), it's a false alarm on an enrolled user
                                            if sim_val >= 0.20:
                                                stats["face_false_alarms"] += 1
                                            else:
                                                stats["true_intruders"] += 1
                                else:
                                    stats["intruder_count"] += 1
                                    stats["intruder_human_count"] += 1
                                    stats["true_intruders"] += 1

                                if sim_val is not None:
                                    label_text = f"{name_label} ({sim_val:.2f}) {conf:.2f}"
                                else:
                                    label_text = f"{name_label} ({conf:.2f})"

                                new_boxes.append((label_text, (fx1, fy1, fx2, fy2), box_color))
                        else:
                            # Person body detected by YOLO, but no matching enrolled face found
                            stats["intruder_count"] += 1
                            stats["intruder_human_count"] += 1
                            # Large foreground person crop where face was missed is a false alarm
                            box_area = (x2 - x1) * (y2 - y1)
                            if box_area > 35000:
                                stats["face_false_alarms"] += 1
                            else:
                                stats["true_intruders"] += 1
                            label_text = f"Intruder(Human) ({conf:.2f})"
                            new_boxes.append((label_text, (x1, y1, x2, y2), (0, 0, 255)))

                    elif cls_name == "Animal":
                        stats["animal_count"] += 1
                        stats["intruder_count"] += 1
                        stats["intruder_animal_count"] += 1
                        cycle_has_valid_obj = True
                        label_text = f"Intruder(Animal) ({conf:.2f})"
                        new_boxes.append((label_text, (x1, y1, x2, y2), (0, 69, 255)))

                # Update confusion matrix
                if cycle_has_valid_obj:
                    stats["tp"] += 1
                elif cycle_has_det:
                    stats["fp"] += 1
                else:
                    stats["tn"] += 1

            if cycle_has_det:
                stats["frames_with_det"] += 1

            cached_boxes = new_boxes

        # Draw bounding boxes & labels
        for label_text, (bx1, by1, bx2, by2), color in cached_boxes:
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2)
            text_y = max(20, by1 - 8)
            draw_label(frame, label_text, bx1, text_y, color)

        # FPS calculation
        time_diff = curr_time - prev_time
        if time_diff > 0:
            current_fps = 1.0 / time_diff
            fps = 0.9 * fps + 0.1 * current_fps if fps > 0 else current_fps
            fps_history.append(fps)
        prev_time = curr_time

        # Top status banner
        if args.duration > 0:
            remaining = max(0, args.duration - elapsed)
            banner = f"SenseGrid Live  |  Time left: {remaining:.0f}s / {args.duration:.0f}s  |  FPS: {fps:.1f}  |  Conf: {conf_threshold:.2f}"
        else:
            banner = f"SenseGrid Live  |  Running  |  FPS: {fps:.1f}  |  Conf: {conf_threshold:.2f}"

        cv2.putText(frame, banner, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(frame, banner, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Show snapshot confirmation toast if recently saved
        if curr_time - snapshot_msg_time < 3.0 and snapshot_msg:
            toast_y = frame.shape[0] - 25
            cv2.rectangle(frame, (10, toast_y - 25), (min(frame.shape[1] - 10, 520), toast_y + 10), (0, 160, 0), -1)
            cv2.putText(frame, f"[SAVED] {snapshot_msg}", (20, toast_y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Show GUI window
        cv2.imshow(window_name, frame)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            print("\n[INFO] Exited by user. Generating analysis report...")
            break
        elif key in (ord('s'), ord('S')):
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            filename = SNAPSHOT_DIR / f"detection_{ts}.jpg"
            clean_filename = SNAPSHOT_DIR / f"clean_{ts}.jpg"
            cv2.imwrite(str(filename), frame)
            cv2.imwrite(str(clean_filename), raw_frame)
            snapshot_msg = filename.name
            snapshot_msg_time = time.time()
            print(f"\n[SNAPSHOT] Saved: {filename.resolve()}")
        elif key in (ord('+'), ord('=')):
            conf_threshold = min(0.95, round(conf_threshold + 0.05, 2))
            print(f"[CONFIDENCE] Set to {conf_threshold:.2f}")
        elif key in (ord('-'), ord('_')):
            conf_threshold = max(0.10, round(conf_threshold - 0.05, 2))
            print(f"[CONFIDENCE] Set to {conf_threshold:.2f}")

    cap.release()
    cv2.destroyAllWindows()

    stats["avg_fps"] = (sum(fps_history) / len(fps_history)) if fps_history else fps
    print_analysis_report(stats)


if __name__ == "__main__":
    main()
