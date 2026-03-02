"""
Webcam Intruder Detection Service

Hardware-agnostic webcam capture service that periodically captures frames,
runs intruder detection, and triggers alerts for Human detections.

Works on:
- Windows (laptop webcam)
- Raspberry Pi (USB camera or Pi Camera via OpenCV)
"""

import cv2
import time
import threading
import os
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class WebcamConfig:
    """Configuration for webcam service."""
    camera_index: int = 0
    capture_interval: float = 5.0  # Seconds between frame captures
    alert_cooldown: float = 60.0   # Seconds between alerts for same detection
    resolution_width: int = 640
    resolution_height: int = 480
    confidence_threshold: float = 0.5
    target_classes: List[str] = field(default_factory=lambda: ["Human"])
    detector_type: str = "roboflow"
    
    @classmethod
    def from_env(cls) -> "WebcamConfig":
        """Load configuration from environment variables."""
        return cls(
            camera_index=int(os.getenv("WEBCAM_CAMERA_INDEX", "0")),
            capture_interval=float(os.getenv("WEBCAM_CAPTURE_INTERVAL", "5.0")),
            alert_cooldown=float(os.getenv("WEBCAM_ALERT_COOLDOWN", "60.0")),
            resolution_width=int(os.getenv("WEBCAM_RESOLUTION_WIDTH", "640")),
            resolution_height=int(os.getenv("WEBCAM_RESOLUTION_HEIGHT", "480")),
            confidence_threshold=float(os.getenv("WEBCAM_CONFIDENCE_THRESHOLD", "0.5")),
            target_classes=os.getenv("WEBCAM_TARGET_CLASSES", "Human").split(","),
            detector_type=os.getenv("DETECTOR_TYPE", "roboflow").lower(),
        )


@dataclass
class Detection:
    """Single detection result."""
    class_name: str
    confidence: float
    bbox: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


@dataclass
class AlertEvent:
    """Alert event triggered by detection."""
    alert_id: str
    detections: List[Detection]
    frame: Any
    timestamp: float


class WebcamService:
    """Webcam-based intruder detection service."""
    
    def __init__(
        self,
        config: Optional[WebcamConfig] = None,
        on_alert: Optional[Callable[[AlertEvent], None]] = None,
        on_detection: Optional[Callable[[List[Detection], Any], None]] = None,
    ):
        self.config = config or WebcamConfig.from_env()
        self.on_alert = on_alert
        self.on_detection = on_detection
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._preview_thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._detector = None
        self._last_alert_time: float = 0
        self._frame_count: int = 0
        self._detection_count: int = 0
        self._frames_with_detection: int = 0
        self._start_time: float = 0
        self._fps: float = 0.0

        self._preview_enabled = False
        self._preview_frame = None          # latest raw frame (updated at camera fps)
        self._preview_lock = threading.Lock()
        self._latest_detections: List[Detection] = []
        self._lock = threading.Lock()
    
    def _init_detector(self):
        """Initialize the intruder detector based on config."""
        if self.config.detector_type in ("roboflow", "cloud"):
            from services.roboflow_detector import get_roboflow_detector
            self._detector = get_roboflow_detector()
            roboflow_local = os.getenv("ROBOFLOW_LOCAL", "false").lower() == "true"
            mode = "LOCAL SERVER" if roboflow_local else "CLOUD API"
            print(f"[webcam] Using Roboflow detector ({mode})")
        elif self.config.detector_type in ("local", "yolo"):
            from services.local_yolo_detector import get_detector
            self._detector = get_detector()
            print(f"[webcam] Using Local YOLO detector")
        else:
            raise ValueError(f"Unknown detector type: {self.config.detector_type}")
    
    def _init_camera(self) -> bool:
        """Initialize camera capture."""
        self._cap = cv2.VideoCapture(self.config.camera_index)
        
        if not self._cap.isOpened():
            print(f"[webcam] ❌ Failed to open camera {self.config.camera_index}")
            return False
        
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution_height)
        
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[webcam] ✅ Camera opened: {actual_w}x{actual_h}")
        return True
    
    def _preview_loop(self):
        """Fast camera-read loop (~30fps). Owns the camera handle."""
        fps_count = 0
        fps_timer = time.time()

        while self._running:
            if self._cap is None or not self._cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            with self._preview_lock:
                self._preview_frame = frame

            fps_count += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                self._fps = fps_count / (now - fps_timer)
                fps_count = 0
                fps_timer = now

    def _capture_frame(self) -> Optional[Any]:
        """Grab latest frame from the preview thread (non-blocking)."""
        with self._preview_lock:
            if self._preview_frame is None:
                return None
            frame = self._preview_frame.copy()
        self._frame_count += 1
        return frame
    
    def _run_detection(self, frame) -> List[Detection]:
        """Run detection on a frame."""
        if self._detector is None:
            return []
        
        try:
            # Check if detector supports direct frame detection
            if hasattr(self._detector, 'detect_from_frame'):
                raw_detections = self._detector.detect_from_frame(
                    frame, conf=self.config.confidence_threshold
                )
            elif hasattr(self._detector, 'detect_from_bytes'):
                _, buffer = cv2.imencode('.jpg', frame)
                raw_detections = self._detector.detect_from_bytes(
                    buffer.tobytes(), conf=self.config.confidence_threshold
                )
            else:
                # Fallback: save to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                    temp_path = f.name
                    cv2.imwrite(temp_path, frame)
                
                try:
                    raw_detections = self._detector.detect(
                        temp_path, conf=self.config.confidence_threshold
                    )
                finally:
                    os.unlink(temp_path)
            
            return [Detection(
                class_name=d.get("class", "Unknown"),
                confidence=d.get("confidence", 0),
                bbox=d.get("bbox", {})
            ) for d in raw_detections]
            
        except Exception as e:
            print(f"[webcam] ⚠️ Detection error: {e}")
            return []
    
    def _filter_target_detections(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to only include target classes (Human by default)."""
        return [d for d in detections if d.class_name in self.config.target_classes]
    
    def _check_cooldown(self) -> bool:
        """Check if cooldown period has passed since last alert."""
        return time.time() - self._last_alert_time >= self.config.alert_cooldown
    
    def _trigger_alert(self, detections: List[Detection], frame) -> AlertEvent:
        """Create and trigger an alert event."""
        alert_id = f"webcam-alert-{int(time.time() * 1000)}"
        
        event = AlertEvent(
            alert_id=alert_id,
            detections=detections,
            frame=frame,
            timestamp=time.time()
        )
        
        self._last_alert_time = time.time()
        self._detection_count += 1
        
        class_summary = ", ".join(f"{d.class_name}({d.confidence:.2f})" for d in detections)
        print(f"[webcam] 🚨 ALERT {alert_id}: {class_summary}")
        
        if self.on_alert:
            try:
                self.on_alert(event)
            except Exception as e:
                print(f"[webcam] ⚠️ Alert callback error: {e}")
        
        return event
    
    def _capture_loop(self):
        """Detection loop - runs inference at capture_interval, decoupled from camera fps."""
        print(f"[webcam] 🎥 Starting detection loop (interval={self.config.capture_interval}s, cooldown={self.config.alert_cooldown}s)")
        self._start_time = time.time()

        # Wait for preview thread to deliver first frame
        while self._running:
            with self._preview_lock:
                ready = self._preview_frame is not None
            if ready:
                break
            time.sleep(0.05)

        while self._running:
            loop_start = time.time()

            frame = self._capture_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            all_detections = self._run_detection(frame)

            with self._lock:
                self._latest_detections = all_detections
            
            if self.on_detection and all_detections:
                try:
                    self.on_detection(all_detections, frame)
                except Exception as e:
                    print(f"[webcam] ⚠️ Detection callback error: {e}")
            
            target_detections = self._filter_target_detections(all_detections)
            
            if target_detections:
                self._frames_with_detection += 1
            
            if target_detections and self._check_cooldown():
                self._trigger_alert(target_detections, frame)
            elif target_detections:
                remaining = self.config.alert_cooldown - (time.time() - self._last_alert_time)
                print(f"[webcam] 👤 Human detected, cooldown active ({remaining:.1f}s remaining)")
            
            elapsed = time.time() - loop_start
            sleep_time = max(0, self.config.capture_interval - elapsed)
            
            sleep_end = time.time() + sleep_time
            while self._running and time.time() < sleep_end:
                time.sleep(0.1)
        
        print("[webcam] 🛑 Capture loop stopped")
    
    def start(self, preview: bool = False) -> bool:
        """Start the webcam service."""
        if self._running:
            print("[webcam] Already running")
            return True
        
        self._preview_enabled = preview
        
        try:
            self._init_detector()
        except Exception as e:
            print(f"[webcam] ❌ Failed to initialize detector: {e}")
            return False
        
        if not self._init_camera():
            return False
        
        self._running = True

        # Fast preview thread - reads camera at full fps
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()

        # Detection thread - runs inference at capture_interval
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        print("[webcam] ✅ Service started")
        return True
    
    def stop(self):
        """Stop the webcam service."""
        if not self._running:
            return
        
        print("[webcam] Stopping service...")
        self._running = False

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        if self._preview_thread:
            self._preview_thread.join(timeout=3)
            self._preview_thread = None

        if self._cap:
            self._cap.release()
            self._cap = None

        print("[webcam] ✅ Service stopped")
    
    def get_latest_frame(self):
        """Get the latest camera frame + most recent detections (for preview)."""
        with self._preview_lock:
            frame = self._preview_frame.copy() if self._preview_frame is not None else None
        with self._lock:
            detections = self._latest_detections.copy()
        return frame, detections
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        accuracy = (self._frames_with_detection / self._frame_count * 100) if self._frame_count > 0 else 0.0
        return {
            "running": self._running,
            "frame_count": self._frame_count,
            "detection_count": self._detection_count,
            "frames_with_detection": self._frames_with_detection,
            "accuracy": accuracy,
            "elapsed_seconds": elapsed,
            "fps": round(self._fps, 1),
            "last_alert_time": self._last_alert_time,
            "config": {
                "camera_index": self.config.camera_index,
                "capture_interval": self.config.capture_interval,
                "alert_cooldown": self.config.alert_cooldown,
                "target_classes": self.config.target_classes,
                "detector_type": self.config.detector_type,
            }
        }
    
    @property
    def is_running(self) -> bool:
        return self._running


def draw_detections(frame, detections: List[Detection], target_classes: List[str] = None):
    """Draw bounding boxes on frame for preview."""
    target_classes = target_classes or ["Human"]
    
    for det in detections:
        bbox = det.bbox
        if isinstance(bbox, list):
            # Local YOLO format: [x1, y1, x2, y2]
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        else:
            # Roboflow format: {"x": cx, "y": cy, "width": w, "height": h}
            x, y = bbox.get("x", 0), bbox.get("y", 0)
            w, h = bbox.get("width", 0), bbox.get("height", 0)
            x1, y1 = int(x - w / 2), int(y - h / 2)
            x2, y2 = int(x + w / 2), int(y + h / 2)
        
        color = (0, 255, 0) if det.class_name in target_classes else (0, 255, 255)
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        label = f"{det.class_name}: {det.confidence:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    
    return frame
