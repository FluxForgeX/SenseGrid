"""
Abstract Intruder Detection Interface

This module defines the base interface that all intruder detection
implementations must follow. This abstraction allows the system to
swap between different detection backends (Roboflow Cloud API, local
YOLO model, etc.) without changing the rest of the codebase.

Detection implementations should inherit from IntruderDetector and
implement the detect() method.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IntruderDetector(ABC):
    """
    Abstract base class for intruder detection systems.
    
    All detector implementations must inherit from this class and
    implement the detect() method to provide a consistent interface
    for the backend API.
    """
    
    @abstractmethod
    def detect(self, image_path: str, conf: float = 0.5) -> List[Dict[str, Any]]:
        """
        Detect humans/intruders in an image.
        
        Args:
            image_path: Absolute path to the image file
            conf: Confidence threshold (0.0 to 1.0)
        
        Returns:
            List of detection dictionaries with format:
            [
                {
                    "class": "Human",
                    "confidence": 0.87,
                    "bbox": [x1, y1, x2, y2] or {"x": ..., "y": ..., "width": ..., "height": ...}
                },
                ...
            ]
        
        Raises:
            FileNotFoundError: If image_path does not exist
            ValueError: If image cannot be processed
            Exception: For other inference errors
        """
        pass
    
    def detect_from_bytes(self, image_bytes: bytes, conf: float = 0.5) -> List[Dict[str, Any]]:
        """
        Optional: Detect from image bytes instead of file path.
        
        Default implementation saves to temp file and calls detect().
        Subclasses can override for more efficient implementations.
        
        Args:
            image_bytes: Raw image data
            conf: Confidence threshold
        
        Returns:
            Same format as detect()
        """
        import tempfile
        import os
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp.write(image_bytes)
            temp_path = tmp.name
        
        try:
            return self.detect(temp_path, conf=conf)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)


class DetectorFactory:
    """
    Factory class to create detector instances based on configuration.
    
    Usage:
        detector = DetectorFactory.create('roboflow')
        detector = DetectorFactory.create('local')
    """
    
    _detectors = {}
    
    @classmethod
    def register(cls, name: str, detector_class):
        """Register a detector implementation."""
        cls._detectors[name] = detector_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> IntruderDetector:
        """
        Create a detector instance by name.
        
        Args:
            name: Detector type ('roboflow', 'local', etc.)
            **kwargs: Arguments to pass to detector constructor
        
        Returns:
            IntruderDetector instance
        
        Raises:
            ValueError: If detector name not registered
        """
        if name not in cls._detectors:
            available = ', '.join(cls._detectors.keys())
            raise ValueError(
                f"Unknown detector '{name}'. Available: {available}"
            )
        
        return cls._detectors[name](**kwargs)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """Get list of registered detector names."""
        return list(cls._detectors.keys())
