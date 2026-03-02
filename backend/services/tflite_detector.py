"""
TFLite Intruder Detection Service (Raspberry Pi Optimized)

This is a lightweight alternative to the PyTorch-based local_yolo_detector.
Optimized for Raspberry Pi using TensorFlow Lite runtime with INT8 quantized model.

Requirements:
    - tflite-runtime (pip install tflite-runtime)
    - numpy
    - opencv-python (cv2)
    - Model file: best_int8.tflite in backend/models/ (or set DETECTOR_MODEL_PATH)

Usage:
    detector = TFLiteDetector()
    detections = detector.detect("path/to/image.jpg")

Environment Variables:
    DETECTOR_MODEL_PATH: Path to .tflite model file (default: backend/models/best_int8.tflite)
    DETECTOR_CONFIDENCE: Default confidence threshold (default: 0.5)
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .intruder_detector import IntruderDetector, DetectorFactory

# Default model path
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_int8.tflite"

# Model configuration (from metadata.yaml)
MODEL_INPUT_SIZE = (416, 416)  # Width, Height
CLASS_NAMES = {0: "Animal", 1: "Human"}


class TFLiteDetector(IntruderDetector):
    """
    TensorFlow Lite-based intruder detection service.
    
    Optimized for Raspberry Pi using INT8 quantized YOLO model.
    Uses tflite-runtime for minimal footprint (~2MB vs 400MB+ for full TensorFlow).
    
    Model Configuration:
        - Input: 416x416 RGB image
        - Output: YOLO detection format
        - Classes: {0: Animal, 1: Human}
    """
    
    def __init__(self, model_path: str = None, confidence: float = None):
        """
        Initialize the TFLite detector.
        
        Args:
            model_path: Path to .tflite model file. 
                       Defaults to DETECTOR_MODEL_PATH env var or backend/models/best_int8.tflite
            confidence: Default confidence threshold (0.0-1.0).
                       Defaults to DETECTOR_CONFIDENCE env var or 0.5
        """
        # Resolve model path
        self.model_path = model_path or os.getenv("DETECTOR_MODEL_PATH", str(DEFAULT_MODEL_PATH))
        self.model_path = Path(self.model_path)
        
        # Default confidence threshold
        self.default_confidence = confidence or float(os.getenv("DETECTOR_CONFIDENCE", "0.5"))
        
        # Validate model file exists
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"TFLite model not found at: {self.model_path}\n"
                f"Please either:\n"
                f"  1. Copy your model to: backend/models/best_int8.tflite\n"
                f"  2. Set DETECTOR_MODEL_PATH environment variable to your model path\n"
                f"\nAvailable models in weights/best_saved_model/:\n"
                f"  - best_int8.tflite (recommended for Raspberry Pi)\n"
                f"  - best_float16.tflite (if GPU available)\n"
                f"  - best_float32.tflite (highest accuracy)"
            )
        
        # Load TFLite model
        try:
            # Try tflite-runtime first (lightweight, preferred for Pi)
            import tflite_runtime.interpreter as tflite
            self.interpreter = tflite.Interpreter(model_path=str(self.model_path))
        except ImportError:
            # Fall back to full TensorFlow if tflite-runtime not available
            try:
                import tensorflow as tf
                self.interpreter = tf.lite.Interpreter(model_path=str(self.model_path))
            except ImportError:
                raise ImportError(
                    "Neither tflite-runtime nor tensorflow is installed.\n"
                    "Install tflite-runtime (recommended for Raspberry Pi):\n"
                    "  pip install tflite-runtime\n"
                    "Or install tensorflow:\n"
                    "  pip install tensorflow"
                )
        
        # Allocate tensors
        self.interpreter.allocate_tensors()
        
        # Get input/output details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Get input shape and type
        self.input_shape = self.input_details[0]['shape']  # e.g., [1, 416, 416, 3]
        self.input_dtype = self.input_details[0]['dtype']
        
        # Check if model uses quantization
        self.is_quantized = self.input_dtype == np.uint8 or self.input_dtype == np.int8
        
        # Get quantization parameters if quantized
        if self.is_quantized:
            self.input_scale = self.input_details[0].get('quantization', (1.0, 0))[0]
            self.input_zero_point = self.input_details[0].get('quantization', (1.0, 0))[1]
            # Handle quantization_parameters format
            if 'quantization_parameters' in self.input_details[0]:
                quant_params = self.input_details[0]['quantization_parameters']
                if 'scales' in quant_params and len(quant_params['scales']) > 0:
                    self.input_scale = quant_params['scales'][0]
                if 'zero_points' in quant_params and len(quant_params['zero_points']) > 0:
                    self.input_zero_point = quant_params['zero_points'][0]
        
        print(f"✅ TFLite detector loaded: {self.model_path.name}")
        print(f"   Input shape: {self.input_shape}, dtype: {self.input_dtype}")
        print(f"   Quantized: {self.is_quantized}")
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input.
        
        Args:
            image: BGR image from OpenCV (H, W, C)
        
        Returns:
            Preprocessed image tensor (1, 416, 416, 3)
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize to model input size
        height, width = self.input_shape[1], self.input_shape[2]
        image_resized = cv2.resize(image_rgb, (width, height))
        
        # Add batch dimension
        image_batch = np.expand_dims(image_resized, axis=0)
        
        # Handle quantization or normalization
        if self.is_quantized:
            # For INT8/UINT8 models, keep as uint8 (model handles quantization internally)
            if self.input_dtype == np.uint8:
                return image_batch.astype(np.uint8)
            elif self.input_dtype == np.int8:
                # Convert to int8 range
                return (image_batch.astype(np.float32) - 128).astype(np.int8)
        else:
            # For float models, normalize to [0, 1]
            return (image_batch / 255.0).astype(np.float32)
        
        return image_batch
    
    def _postprocess(self, outputs: List[np.ndarray], original_shape: Tuple[int, int],
                     conf_threshold: float = 0.5, iou_threshold: float = 0.45) -> List[Dict[str, Any]]:
        """
        Postprocess YOLO model outputs to get detections.
        
        Args:
            outputs: Raw model output tensors
            original_shape: Original image (height, width)
            conf_threshold: Confidence threshold for filtering
            iou_threshold: IoU threshold for NMS
        
        Returns:
            List of detection dictionaries
        """
        detections = []
        orig_h, orig_w = original_shape
        input_h, input_w = self.input_shape[1], self.input_shape[2]
        
        # Get the main output tensor
        output = outputs[0]
        
        # Handle different output formats
        # YOLOv8 TFLite typically outputs shape: [1, num_detections, 6] or [1, 6, num_detections]
        # Format: [x_center, y_center, width, height, confidence, class_id] or similar
        
        if len(output.shape) == 3:
            output = output[0]  # Remove batch dimension
        
        # Check if we need to transpose (YOLOv8 format)
        if output.shape[0] < output.shape[1] if len(output.shape) == 2 else False:
            output = output.T
        
        # Handle YOLOv8 output format: [x, y, w, h, class1_conf, class2_conf, ...]
        # or YOLO format with [x, y, w, h, obj_conf, class1, class2, ...]
        
        for detection in output:
            if len(detection) < 5:
                continue
            
            # Try to parse as YOLOv8 format: [x, y, w, h, class_scores...]
            x_center, y_center, w, h = detection[:4]
            class_scores = detection[4:]
            
            if len(class_scores) == 0:
                continue
            
            # Get best class
            class_id = int(np.argmax(class_scores))
            confidence = float(class_scores[class_id])
            
            # Apply confidence threshold
            if confidence < conf_threshold:
                continue
            
            # Only keep Human detections (class_id == 1)
            if class_id != 1:
                continue
            
            # Convert from normalized/model coords to original image coords
            # Handle both normalized (0-1) and pixel coordinates
            if x_center <= 1.0 and y_center <= 1.0:
                # Normalized coordinates
                x_center *= orig_w
                y_center *= orig_h
                w *= orig_w
                h *= orig_h
            else:
                # Pixel coordinates relative to input size
                x_center = x_center / input_w * orig_w
                y_center = y_center / input_h * orig_h
                w = w / input_w * orig_w
                h = h / input_h * orig_h
            
            # Convert from center format to corner format
            x1 = int(x_center - w / 2)
            y1 = int(y_center - h / 2)
            x2 = int(x_center + w / 2)
            y2 = int(y_center + h / 2)
            
            # Clamp to image bounds
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))
            
            detections.append({
                "class": CLASS_NAMES.get(class_id, f"class_{class_id}"),
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2]
            })
        
        # Apply NMS if multiple detections
        if len(detections) > 1:
            detections = self._nms(detections, iou_threshold)
        
        return detections
    
    def _nms(self, detections: List[Dict], iou_threshold: float = 0.45) -> List[Dict]:
        """
        Apply Non-Maximum Suppression to filter overlapping detections.
        """
        if len(detections) == 0:
            return []
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        kept = []
        while detections:
            best = detections.pop(0)
            kept.append(best)
            
            detections = [
                d for d in detections
                if self._iou(best['bbox'], d['bbox']) < iou_threshold
            ]
        
        return kept
    
    def _iou(self, box1: List[int], box2: List[int]) -> float:
        """Calculate Intersection over Union between two boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0
    
    def detect(self, image_path: str, conf: float = None, iou: float = 0.45) -> List[Dict[str, Any]]:
        """
        Detect humans/intruders in an image file.
        
        Args:
            image_path: Path to image file
            conf: Confidence threshold (default: self.default_confidence)
            iou: IoU threshold for NMS (default: 0.45)
        
        Returns:
            List of Human detections:
            [{"class": "Human", "confidence": 0.87, "bbox": [x1, y1, x2, y2]}, ...]
        
        Raises:
            ValueError: If image cannot be loaded
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Image could not be loaded from {image_path}")
        
        return self.detect_from_frame(image, conf=conf, iou=iou)
    
    def detect_from_frame(self, frame: np.ndarray, conf: float = None, 
                          iou: float = 0.45) -> List[Dict[str, Any]]:
        """
        Detect humans in a video frame (numpy array).
        
        Args:
            frame: OpenCV BGR image (numpy array)
            conf: Confidence threshold
            iou: IoU threshold for NMS
        
        Returns:
            List of Human detections
        """
        conf = conf if conf is not None else self.default_confidence
        original_shape = frame.shape[:2]  # (height, width)
        
        # Preprocess
        input_tensor = self._preprocess(frame)
        
        # Run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
        self.interpreter.invoke()
        
        # Get outputs
        outputs = []
        for output_detail in self.output_details:
            output = self.interpreter.get_tensor(output_detail['index'])
            
            # Dequantize if needed
            if 'quantization_parameters' in output_detail:
                quant = output_detail['quantization_parameters']
                if 'scales' in quant and len(quant['scales']) > 0:
                    scale = quant['scales'][0]
                    zero_point = quant['zero_points'][0] if 'zero_points' in quant else 0
                    output = (output.astype(np.float32) - zero_point) * scale
            
            outputs.append(output)
        
        # Postprocess
        detections = self._postprocess(outputs, original_shape, conf, iou)
        
        return detections
    
    def detect_with_visualization(self, image_path: str, conf: float = None,
                                  iou: float = 0.45) -> Tuple[List[Dict], np.ndarray]:
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
        
        detections = self.detect_from_frame(image, conf=conf, iou=iou)
        annotated = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            confidence = det['confidence']
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"Human {confidence:.2f}"
            cv2.putText(annotated, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return detections, annotated


# Register with factory
DetectorFactory.register('tflite', TFLiteDetector)
DetectorFactory.register('tflite-int8', TFLiteDetector)  # Alias


# Singleton instance (lazy-loaded)
_detector_instance = None


def get_detector(model_path: str = None) -> TFLiteDetector:
    """
    Get or create the singleton TFLiteDetector instance.
    
    Args:
        model_path: Optional custom model path (only used on first call)
    
    Returns:
        TFLiteDetector: Shared detector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TFLiteDetector(model_path=model_path)
    return _detector_instance
