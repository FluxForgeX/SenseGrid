"""
Local YOLO Intruder Detection Service (OFFLINE OPTION)

This is an ALTERNATIVE to Roboflow Cloud API.
Uses local YOLO model (best.pt) for offline inference.
NO Roboflow API is used at runtime.

Requirements:
    - best.pt model file in backend/models/
    - ultralytics and opencv-python installed
    - Works without internet connection

Usage:
    detector = LocalYOLODetector()
    detections = detector.detect("path/to/image.jpg")
"""

from ultralytics import YOLO
import cv2
from pathlib import Path
import os
from typing import List, Dict, Any

from .intruder_detector import IntruderDetector, DetectorFactory

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best.pt"


class LocalYOLODetector(IntruderDetector):
    """
    Local YOLO-based intruder detection service (OFFLINE).
    
    Uses Ultralytics YOLO with a custom-trained model (best.pt)
    to detect humans in images or video frames.
    
    The model file must be placed at: backend/models/best.pt
    """
    """
    Local YOLO-based intruder detection service.
    
    Uses Ultralytics YOLO with a custom-trained model (best.pt)
    to detect humans in images or video frames.
    
    The model file must be placed at: backend/models/best.pt
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the intruder detector with YOLO model.
        
        Args:
            model_path: Optional custom path to model file.
                       Defaults to backend/models/best.pt
        """
        self.model_path = model_path or MODEL_PATH
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model file not found at {self.model_path}\n"
                f"Please place your trained best.pt model in backend/models/"
            )
        
        # Load YOLO model
        self.model = YOLO(str(self.model_path))
        print(f"✅ Local YOLO detector loaded from {self.model_path}")
    
    def detect(self, image_path: str, conf=0.5, iou=0.35) -> List[Dict[str, Any]]:
        """
        Runs intruder detection on a single image file.
        
        Implements IntruderDetector.detect() interface.
        
        Args:
            image_path: Path to image file
            conf: Confidence threshold (default 0.5)
            iou: IoU threshold for NMS (default 0.35)
        
        Returns:
            List of detections where class == 'Human':
            [
                {
                    "class": "Human",
                    "confidence": 0.87,
                    "bbox": [x1, y1, x2, y2]
                },
                ...
            ]
        
        Raises:
            ValueError: If image cannot be loaded
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Image could not be loaded from {image_path}")
        
        return self.detect_from_frame(image, conf=conf, iou=iou)
        """
        Runs intruder detection on a single image file.
        
        Args:
            image_path: Path to image file
            conf: Confidence threshold (default 0.5)
            iou: IoU threshold for NMS (default 0.35)
        
        Returns:
            List of detections where class == 'Human':
            [
                {
                    "class": "Human",
                    "confidence": 0.87,
                    "bbox": [x1, y1, x2, y2]
                },
                ...
            ]
        
        Raises:
            ValueError: If image cannot be loaded
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Image could not be loaded from {image_path}")
        
        return self.detect_from_frame(image, conf=conf, iou=iou)
    
    def detect_from_frame(self, frame, conf=0.5, iou=0.35):
        """
        Runs intruder detection on a numpy array (video frame).
        
        Args:
            frame: OpenCV image (numpy array)
            conf: Confidence threshold (default 0.5)
            iou: IoU threshold for NMS (default 0.35)
        
        Returns:
            List of Human detections (same format as detect_from_image)
        """
        # Run YOLO inference
        results = self.model(frame, conf=conf, iou=iou, verbose=False)
        
        detections = []
        
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                label = self.model.names[class_id]
                
                # Only return Human detections
                if label == "Human":
                    detections.append({
                        "class": label,
                        "confidence": float(box.conf[0]),
                        "bbox": box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    })
        
        return detections
    
    def detect_with_visualization(self, image_path: str, conf=0.5, iou=0.35):
        """
        Detect humans and return annotated image.
        
        Args:
            image_path: Path to image file
            conf: Confidence threshold
            iou: IoU threshold
        
        Returns:
            Tuple of (detections, annotated_frame)
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Image could not be loaded from {image_path}")
        
        results = self.model(image, conf=conf, iou=iou, verbose=False)
        
        detections = []
        annotated_frame = image.copy()
        
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                label = self.model.names[class_id]
                
                if label == "Human":
                    # Extract box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    confidence = float(box.conf[0])
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw label
                    label_text = f"Human {confidence:.2f}"
                    cv2.putText(
                        annotated_frame,
                        label_text,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )
                    
                    detections.append({
                        "class": label,
                        "confidence": confidence,
                        "bbox": [x1, y1, x2, y2]
                    })
        
        return detections, annotated_frame


# Register with factory
DetectorFactory.register('local', LocalYOLODetector)
DetectorFactory.register('yolo', LocalYOLODetector)  # Alias


# Singleton instance (lazy-loaded)
_detector_instance = None


def get_detector():
    """
    Get or create the singleton LocalYOLODetector instance.
    
    Returns:
        LocalYOLODetector: Shared detector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = LocalYOLODetector()
    return _detector_instance
