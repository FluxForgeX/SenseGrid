"""
Face Recognition Service for SenseGrid Intruder Detection

Uses DeepFace with ArcFace model to:
1. Detect faces in cropped person regions
2. Generate face embeddings (512-dim vectors)
3. Compare against enrolled (authorized) face embeddings
4. Classify as "Authorized" or "Intruder"

Enrollment:
    - Capture face images of authorized people
    - Extract and store embeddings in known_faces.json

Recognition:
    - Extract embedding from detected face
    - Compare with stored embeddings using cosine similarity
    - If similarity > threshold → Authorized, else → Intruder
"""

import json
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
KNOWN_FACES_PATH = BACKEND_DIR / "models" / "known_faces.json"

# Recognition threshold (cosine similarity)
# Higher = stricter matching. Tune based on testing.
SIMILARITY_THRESHOLD = 0.55

# Minimum face size in pixels (ignore tiny faces)
MIN_FACE_SIZE = 40

# Check if DeepFace is available (not installed on Raspberry Pi by default)
try:
    from deepface import DeepFace as _DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("⚠️  DeepFace not installed — face recognition disabled (Pi fallback mode)")
    print("   All detected persons will trigger alerts (YOLO-only mode)")
    print("   To enable face recognition: pip install deepface tf-keras")


class FaceRecognizer:
    """
    Face recognition service using DeepFace + ArcFace.

    Handles:
    - Face detection within person bounding boxes
    - Face embedding extraction
    - Comparison against enrolled faces
    - Enrollment of new authorized faces
    """

    def __init__(self):
        self._deepface = None
        self._known_faces = None
        self._initialized = False

    def is_available(self) -> bool:
        """Return True if DeepFace is installed and face recognition is possible."""
        return DEEPFACE_AVAILABLE

    def _ensure_initialized(self):
        """Lazy-load DeepFace to avoid slow import at startup."""
        if self._initialized:
            return
        if not DEEPFACE_AVAILABLE:
            raise ImportError("DeepFace is not installed (Pi fallback mode active)")
        self._deepface = _DeepFace
        self._initialized = True
        print("✅ FaceRecognizer initialized (DeepFace + ArcFace)")

    def _load_known_faces(self) -> Dict[str, Any]:
        """Load enrolled face embeddings from JSON file."""
        if self._known_faces is not None:
            return self._known_faces

        if KNOWN_FACES_PATH.exists():
            with open(KNOWN_FACES_PATH, "r") as f:
                self._known_faces = json.load(f)
        else:
            self._known_faces = {"persons": []}

        return self._known_faces

    def _save_known_faces(self, data: Dict[str, Any]):
        """Save enrolled face embeddings to JSON file."""
        KNOWN_FACES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(KNOWN_FACES_PATH, "w") as f:
            json.dump(data, f, indent=2)
        # Invalidate cache so next load picks up changes
        self._known_faces = None

    def has_enrolled_faces(self) -> bool:
        """Check if any faces have been enrolled."""
        data = self._load_known_faces()
        return len(data.get("persons", [])) > 0

    def get_enrolled_persons(self) -> List[str]:
        """Return list of enrolled person names."""
        data = self._load_known_faces()
        return [p["name"] for p in data.get("persons", [])]

    def enroll_face(self, name: str, image: np.ndarray) -> Dict[str, Any]:
        """
        Enroll an authorized person's face.

        Args:
            name: Person's name/identifier
            image: Face image (numpy array, BGR)

        Returns:
            {"status": "ok", "name": name, "embeddings_count": int}
        """
        self._ensure_initialized()

        # Extract embedding from the face image
        try:
            result = self._deepface.represent(
                img_path=image,
                model_name="ArcFace",
                detector_backend="opencv",
                enforce_detection=True,
            )
        except Exception as e:
            return {"status": "error", "message": f"No face detected: {e}"}

        if not result:
            return {"status": "error", "message": "No face found in image"}

        embedding = result[0]["embedding"]

        # Load existing data
        data = self._load_known_faces()
        persons = data.get("persons", [])

        # Find existing person or create new
        person_entry = None
        for p in persons:
            if p["name"] == name:
                person_entry = p
                break

        if person_entry is None:
            person_entry = {"name": name, "embeddings": []}
            persons.append(person_entry)

        person_entry["embeddings"].append(embedding)
        data["persons"] = persons

        self._save_known_faces(data)

        return {
            "status": "ok",
            "name": name,
            "embeddings_count": len(person_entry["embeddings"]),
        }

    def delete_person(self, name: str) -> bool:
        """Remove an enrolled person and their embeddings."""
        data = self._load_known_faces()
        persons = data.get("persons", [])
        original_count = len(persons)
        data["persons"] = [p for p in persons if p["name"] != name]

        if len(data["persons"]) < original_count:
            self._save_known_faces(data)
            return True
        return False

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

    def recognize_face(self, face_image: np.ndarray) -> Dict[str, Any]:
        """
        Recognize a face against enrolled faces.

        Args:
            face_image: Cropped face image (numpy array, BGR)

        Returns:
            {
                "recognized": bool,
                "name": str or None,
                "similarity": float,
                "status": "authorized" | "intruder" | "no_face" | "no_enrolled" | "unavailable"
            }
        """
        if not DEEPFACE_AVAILABLE:
            return {
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "unavailable",
            }
        self._ensure_initialized()

        if not self.has_enrolled_faces():
            return {
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "no_enrolled",
            }

        # Extract embedding from detected face
        try:
            result = self._deepface.represent(
                img_path=face_image,
                model_name="ArcFace",
                detector_backend="skip",  # face is already cropped
                enforce_detection=False,
            )
        except Exception:
            return {
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "no_face",
            }

        if not result:
            return {
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "no_face",
            }

        query_embedding = result[0]["embedding"]

        # Compare against all enrolled faces
        best_match_name = None
        best_similarity = 0.0

        data = self._load_known_faces()
        for person in data.get("persons", []):
            for stored_embedding in person["embeddings"]:
                sim = self._cosine_similarity(query_embedding, stored_embedding)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match_name = person["name"]

        if best_similarity >= SIMILARITY_THRESHOLD:
            return {
                "recognized": True,
                "name": best_match_name,
                "similarity": round(best_similarity, 4),
                "status": "authorized",
            }
        else:
            return {
                "recognized": False,
                "name": None,
                "similarity": round(best_similarity, 4),
                "status": "intruder",
            }

    def detect_and_recognize_faces(
        self, frame: np.ndarray, person_bbox: List[float]
    ) -> Dict[str, Any]:
        """
        Detect face within a YOLO person bounding box and recognize it.

        Args:
            frame: Full camera frame (numpy array, BGR)
            person_bbox: [x1, y1, x2, y2] from YOLO detection

        Returns:
            {
                "face_found": bool,
                "recognized": bool,
                "name": str or None,
                "similarity": float,
                "status": "authorized" | "intruder" | "no_face" | "no_enrolled" | "unavailable"
            }
        """
        # Pi fallback: DeepFace not installed, skip face recognition
        if not DEEPFACE_AVAILABLE:
            return {
                "face_found": False,
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "unavailable",
            }
        x1, y1, x2, y2 = [int(v) for v in person_bbox]
        h, w = frame.shape[:2]

        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        # Crop person region
        person_crop = frame[y1:y2, x1:x2]
        if person_crop.size == 0:
            return {
                "face_found": False,
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "no_face",
            }

        # Try to detect face in the person crop using OpenCV Haar Cascade
        gray = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE)
        )

        if len(faces) == 0:
            # No face visible (person from behind, too far, etc.)
            return {
                "face_found": False,
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "no_face",
            }

        # Take the largest face detected
        faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        fx, fy, fw, fh = faces_sorted[0]

        # Crop face region
        face_crop = person_crop[fy : fy + fh, fx : fx + fw]
        if face_crop.size == 0 or fw < MIN_FACE_SIZE or fh < MIN_FACE_SIZE:
            return {
                "face_found": False,
                "recognized": False,
                "name": None,
                "similarity": 0.0,
                "status": "no_face",
            }

        # Recognize the face
        recognition = self.recognize_face(face_crop)
        recognition["face_found"] = True
        return recognition


# Singleton instance
_recognizer_instance = None


def get_face_recognizer() -> FaceRecognizer:
    """Get or create singleton FaceRecognizer instance."""
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = FaceRecognizer()
    return _recognizer_instance
