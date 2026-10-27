#!/usr/bin/env python
"""
SenseGrid Face Enrollment Utility

Enrolls a person's face into backend/models/known_faces.json
using your webcam so they are recognized by name in the live detection GUI!

Usage:
    python enroll_face.py --name "YourName"
"""

import sys
import time
import argparse
from pathlib import Path
import cv2

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.face_recognizer import get_face_recognizer, DEEPFACE_AVAILABLE


def main():
    parser = argparse.ArgumentParser(description="Enroll a new face for SenseGrid")
    parser.add_argument("name_pos", nargs="?", default="", help="Name of person to enroll")
    parser.add_argument("--name", "-n", type=str, default="", help="Name of person to enroll")
    parser.add_argument("--auto", "-a", action="store_true", help="Auto-capture face angles hands-free with countdown")
    parser.add_argument("--glasses", "-g", action="store_true", help="Glasses mode: guided enrollment with glasses ON (2 angles) and OFF (2 angles)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    args = parser.parse_args()

    name = (args.name or args.name_pos).strip()
    if not name:
        try:
            name = input("Enter person name to enroll (e.g. Saad, Fardin, Ebrahim): ").strip()
        except EOFError:
            name = "User"

    if not name:
        print("[ERROR] Name cannot be empty.")
        sys.exit(1)

    glasses_mode = args.glasses
    target_angles = 4 if glasses_mode else 3

    print("=" * 60)
    print(f"  Enrolling Face for: {name}")
    if glasses_mode:
        print("  [*] GLASSES MODE ACTIVE (4 Angles Total):")
        print("      - Angles 1 & 2 : Glasses ON  (Frontal + Slight Angle)")
        print("      - Angles 3 & 4 : Glasses OFF (Frontal + Slight Angle)")
    print("=" * 60)

    if not DEEPFACE_AVAILABLE:
        print("[ERROR] DeepFace is not installed. Face recognition is unavailable.")
        sys.exit(1)

    recognizer = get_face_recognizer()

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera)

    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {args.camera}")
        sys.exit(1)

    known_data = recognizer._load_known_faces()
    initial_count = 0
    for p in known_data.get("persons", []):
        if p["name"] == name:
            initial_count = len(p.get("embeddings", []))
            break

    print("\nInstructions:")
    print("  1. Look at the webcam")
    if glasses_mode:
        print("  2. Start with glasses ON, then remove them when prompted")
    else:
        print("  2. Press [SPACE] to capture an angle (or wait if in --auto mode)")
        print("  3. Press [G] to toggle Glasses Mode (captures with & without glasses)")
    print("  4. Press [Q] or [ESC] when finished\n")

    window_name = f"SenseGrid - Enroll Face: {name} (SPACE=Capture, G=Glasses, Q=Finish)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)

    # Face detector cascade for feedback
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    captured = False
    toast_msg = ""
    toast_time = 0.0
    current_count = initial_count
    session_captures = 0
    countdown_start = None
    next_capture_cooldown = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.02)
            continue

        display = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))

        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(display, f"{name}: Ready", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Instructions banner
        mode_str = "AUTO" if args.auto else "SPACE=Capture"
        target_angles = 4 if glasses_mode else 3
        header = f"Enrolling: {name} ({session_captures}/{target_angles}) | {mode_str} | G=Glasses | Q=Done"
        cv2.putText(display, header, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)

        # Glasses Mode guidance prompt
        if glasses_mode:
            if session_captures < 2:
                glasses_prompt = f"[STEP 1/2] Keep GLASSES ON (Angle {session_captures + 1}/2)"
                p_color = (255, 200, 0)
            else:
                glasses_prompt = f"[STEP 2/2] REMOVE GLASSES NOW (Angle {session_captures - 1}/2)"
                p_color = (0, 220, 255)
            cv2.putText(display, glasses_prompt, (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, p_color, 2)

        curr_t = time.time()
        trigger_capture = False

        if args.auto:
            if len(faces) > 0 and curr_t > next_capture_cooldown:
                if countdown_start is None:
                    countdown_start = curr_t
                rem = 3.0 - (curr_t - countdown_start)
                if rem > 0:
                    cv2.putText(display, f"AUTO-CAPTURING in {rem:.1f}s... Hold steady", (10, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 255), 2)
                else:
                    trigger_capture = True
                    countdown_start = None
                    # Give extra time when asking user to remove glasses
                    if glasses_mode and session_captures == 1:
                        next_capture_cooldown = curr_t + 4.5
                    else:
                        next_capture_cooldown = curr_t + 2.5
            else:
                countdown_start = None

        # Show toast message after capture
        if time.time() - toast_time < 3.5 and toast_msg:
            toast_y = 125 if args.auto or glasses_mode else 65
            cv2.putText(display, toast_msg, (10, toast_y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 0), 2)

        cv2.imshow(window_name, display)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord('g'), ord('G')):
            glasses_mode = not glasses_mode
            target_angles = 4 if glasses_mode else 3
            status_txt = "ON (4 angles: with & without)" if glasses_mode else "OFF (3 angles standard)"
            toast_msg = f"[MODE] Glasses Mode: {status_txt}"
            toast_time = time.time()
            print(f"[GLASSES MODE] Toggled to: {status_txt}")

        elif key in (32, 13) or trigger_capture:  # SPACE, ENTER, or AUTO timer
            print(f"[*] Processing face angle for {name} with ArcFace...")
            cv2.putText(display, "Processing...", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(window_name, display)
            cv2.waitKey(100)

            # If face box detected, crop face with generous padding for maximum DeepFace accuracy
            face_img = frame
            if len(faces) > 0:
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                fx, fy, fw, fh = largest_face
                pad_x = int(0.3 * fw)
                pad_y = int(0.3 * fh)
                y1 = max(0, fy - pad_y)
                y2 = min(frame.shape[0], fy + fh + pad_y)
                x1 = max(0, fx - pad_x)
                x2 = min(frame.shape[1], fx + fw + pad_x)
                crop = frame[y1:y2, x1:x2]
                if crop.size > 0:
                    face_img = crop

            result = recognizer.enroll_face(name, face_img)
            if result.get("status") == "ok":
                session_captures += 1
                current_count = result.get("embeddings_count", current_count + 1)
                captured = True
                print(f"[SUCCESS] Angle saved! Total stored angles for {name}: {current_count}")

                if session_captures >= target_angles:
                    print(f"\n[DONE] Great! All {target_angles} angles successfully saved for {name}.")
                    break
                else:
                    if glasses_mode and session_captures == 2:
                        toast_msg = "[PLEASE REMOVE GLASSES] Take off your glasses for step 2!"
                        print(f"\n[ACTION] Please REMOVE your glasses now for the next angles!")
                    else:
                        toast_msg = f"[OK] Angle {session_captures}/{target_angles} saved! Turn head slightly"
                        print(f"[*] Tip: Turn head slightly for angle {session_captures + 1}/{target_angles} (or press Q to finish).")
                    toast_time = time.time()
            else:
                print(f"[WARN] Enrollment failed: {result.get('message')}. Please try again.")

        elif key in (ord('q'), ord('Q'), 27):
            print("[INFO] Finished enrollment.")
            break

    cap.release()
    cv2.destroyAllWindows()

    if captured:
        print(f"\n[DONE] {name} is enrolled with {current_count} angle(s) in backend/models/known_faces.json")
        if glasses_mode:
            print("Both Glasses-ON and Glasses-OFF representations are registered!")
        print("Run .\\run_webcam.bat to see your name recognized live with or without glasses!")


if __name__ == "__main__":
    main()
