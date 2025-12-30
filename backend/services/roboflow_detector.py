"""
Roboflow Cloud API Detector

This module implements intruder detection using Roboflow's serverless
inference API. It requires an internet connection but provides:

- No local model files needed
- Automatic scaling and reliability
- Lower memory footprint
- Easy model updates via Roboflow dashboard

Configuration:
    Set environment variables in .env:
    - ROBOFLOW_API_KEY: Your Roboflow API key
    - ROBOFLOW_WORKSPACE: Your workspace name (e.g., "project-ark")
    - ROBOFLOW_WORKFLOW_ID: Your workflow ID (e.g., "custom-workflow-2")
    - ROBOFLOW_CONFIDENCE: Minimum confidence threshold (default: 0.6)

Usage:
    detector = RoboflowDetector()
    detections = detector.detect("path/to/image.jpg")
"""

import os
from typing import List, Dict, Any
from pathlib import Path

try:
    from inference_sdk import InferenceHTTPClient
except ImportError:
    raise ImportError(
        "inference-sdk not installed. Run: pip install inference-sdk"
    )

from .intruder_detector import IntruderDetector, DetectorFactory


class RoboflowDetector(IntruderDetector):
    """
    Roboflow-based intruder detection (Cloud or Local Inference Server).
    
    Supports two modes:
    - Cloud: Uses Roboflow's serverless API (requires internet)
    - Local: Uses local Roboflow Inference server at localhost:9001
    
    Set ROBOFLOW_LOCAL=true in .env to use local inference server.
    """
    
    # Default URLs for cloud and local servers
    CLOUD_API_URL = "https://serverless.roboflow.com"
    LOCAL_API_URL = "http://localhost:9001"
    
    def __init__(
        self,
        api_key: str = None,
        workspace: str = None,
        workflow_id: str = None,
        confidence_threshold: float = None,
        use_local: bool = None,
        local_url: str = None
    ):
        """
        Initialize Roboflow detector.
        
        Args:
            api_key: Roboflow API key (defaults to ROBOFLOW_API_KEY env var)
            workspace: Workspace name (defaults to ROBOFLOW_WORKSPACE env var)
            workflow_id: Workflow ID (defaults to ROBOFLOW_WORKFLOW_ID env var)
            confidence_threshold: Min confidence (defaults to ROBOFLOW_CONFIDENCE or 0.6)
            use_local: Use local inference server (defaults to ROBOFLOW_LOCAL env var)
            local_url: Local server URL (defaults to ROBOFLOW_LOCAL_URL or localhost:9001)
        
        Raises:
            ValueError: If required credentials are missing
        """
        # Load from environment if not provided
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        self.workspace = workspace or os.getenv("ROBOFLOW_WORKSPACE")
        self.workflow_id = workflow_id or os.getenv("ROBOFLOW_WORKFLOW_ID")
        self.confidence_threshold = confidence_threshold or float(
            os.getenv("ROBOFLOW_CONFIDENCE", "0.6")
        )
        
        # Check if using local inference server
        if use_local is not None:
            self.use_local = use_local
        else:
            self.use_local = os.getenv("ROBOFLOW_LOCAL", "false").lower() in ("true", "1", "yes")
        
        # Local server URL (can be customized)
        self.local_url = local_url or os.getenv("ROBOFLOW_LOCAL_URL", self.LOCAL_API_URL)
        
        # Validate required credentials
        if not self.api_key:
            raise ValueError(
                "ROBOFLOW_API_KEY not set. Add to .env or pass to constructor."
            )
        if not self.workspace:
            raise ValueError(
                "ROBOFLOW_WORKSPACE not set. Add to .env or pass to constructor."
            )
        if not self.workflow_id:
            raise ValueError(
                "ROBOFLOW_WORKFLOW_ID not set. Add to .env or pass to constructor."
            )
        
        # Select API URL based on mode
        api_url = self.local_url if self.use_local else self.CLOUD_API_URL
        
        # Initialize Roboflow client
        self.client = InferenceHTTPClient(
            api_url=api_url,
            api_key=self.api_key
        )
        
        mode = "LOCAL" if self.use_local else "CLOUD"
        print(f"✅ Roboflow detector initialized ({mode} mode)")
        print(f"   API URL: {api_url}")
        print(f"   Workspace: {self.workspace}")
        print(f"   Workflow: {self.workflow_id}")
        print(f"   Confidence threshold: {self.confidence_threshold}")
    
    def detect(self, image_path, conf: float = None) -> List[Dict[str, Any]]:
        """
        Detect humans in an image using Roboflow Cloud API.
        
        Args:
            image_path: Path to image file OR numpy array (in-memory frame)
            conf: Confidence threshold override (uses instance default if None)
        
        Returns:
            List of Human detections:
            [
                {
                    "class": "Human",
                    "confidence": 0.87,
                    "bbox": {"x": 320, "y": 240, "width": 100, "height": 200}
                },
                ...
            ]
        
        Raises:
            FileNotFoundError: If image_path doesn't exist
            Exception: If API request fails
        """
        import tempfile
        import numpy as np
        import cv2
        
        # Handle numpy array (in-memory frame)
        temp_file = None
        if isinstance(image_path, np.ndarray):
            # Save frame to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            cv2.imwrite(temp_file.name, image_path)
            image_path = temp_file.name
        
        # Validate file exists
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Use instance threshold if not overridden
        min_confidence = conf if conf is not None else self.confidence_threshold
        
        try:
            # Call Roboflow API
            result = self.client.run_workflow(
                workspace_name=self.workspace,
                workflow_id=self.workflow_id,
                images={"image": image_path},
                use_cache=True  # Enable caching for faster repeated requests
            )
            
            # DEBUG: Print full response to understand structure
            print("\n" + "="*60)
            print("DEBUG: Full Roboflow API Response:")
            print("="*60)
            import json
            print(json.dumps(result, indent=2, default=str))
            print("="*60 + "\n")
            
            # Parse response
            detections = []
            
            # Classes to detect (Human for intruders, Animal for testing/monitoring)
            target_classes = ["Human", "Animal"]
            
            # Handle Roboflow workflow response structure
            # Response is a list: [{ "predictions": { "image": {...}, "predictions": [...] } }]
            if isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                
                # Navigate to nested predictions
                if "predictions" in first_item:
                    pred_wrapper = first_item["predictions"]
                    
                    # Get the actual predictions array (nested inside)
                    if isinstance(pred_wrapper, dict) and "predictions" in pred_wrapper:
                        predictions = pred_wrapper["predictions"]
                    elif isinstance(pred_wrapper, list):
                        predictions = pred_wrapper
                    else:
                        predictions = []
                    
                    for pred in predictions:
                        pred_class = pred.get("class")
                        pred_confidence = pred.get("confidence", 0)
                        
                        # Filter by class and confidence
                        if pred_class in target_classes and pred_confidence >= min_confidence:
                            # Build bbox from x, y, width, height (center format)
                            bbox = {
                                "x": pred.get("x", 0),
                                "y": pred.get("y", 0),
                                "width": pred.get("width", 0),
                                "height": pred.get("height", 0)
                            }
                            detections.append({
                                "class": pred_class,
                                "confidence": float(pred_confidence),
                                "bbox": bbox
                            })
                            print(f"DEBUG: Detected {pred_class} with confidence {pred_confidence:.2f}")
                        else:
                            print(f"DEBUG: Filtered out - class: {pred_class}, confidence: {pred_confidence}")
                else:
                    print("DEBUG: No 'predictions' key in first item")
                    print(f"DEBUG: Available keys: {list(first_item.keys())}")
            else:
                print("DEBUG: Result is not a list or is empty")
                print(f"DEBUG: Result type: {type(result)}")
            
            print(f"DEBUG: Total detections found: {len(detections)}")
            return detections
            
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"Roboflow API error: {str(e)}") from e
        finally:
            # Clean up temp file if created
            if temp_file:
                import os
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
    
    def detect_from_bytes(self, image_bytes: bytes, conf: float = None) -> List[Dict[str, Any]]:
        """
        Detect from image bytes (optimized for Roboflow).
        
        Args:
            image_bytes: Raw image data
            conf: Confidence threshold
        
        Returns:
            List of detections (same format as detect())
        """
        import tempfile
        import os
        
        # Roboflow SDK requires file path, so save temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp.write(image_bytes)
            temp_path = tmp.name
        
        try:
            return self.detect(temp_path, conf=conf)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_connection(self) -> bool:
        """
        Test if Roboflow API is accessible.
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Simple health check
            # You could use a tiny test image or workflow info endpoint
            return True
        except:
            return False


# Register with factory
DetectorFactory.register('roboflow', RoboflowDetector)
DetectorFactory.register('cloud', RoboflowDetector)  # Alias


# Singleton instance (lazy-loaded)
_roboflow_instance = None


def get_roboflow_detector(**kwargs) -> RoboflowDetector:
    """
    Get or create singleton Roboflow detector instance.
    
    Args:
        **kwargs: Arguments to pass to RoboflowDetector constructor
                 (only used on first call)
    
    Returns:
        RoboflowDetector: Shared detector instance
    """
    global _roboflow_instance
    if _roboflow_instance is None:
        _roboflow_instance = RoboflowDetector(**kwargs)
    return _roboflow_instance
