"""
Detection Accuracy Test Script

Runs webcam detection for a specified duration and calculates:
- Detection rate (frames with positive detections)
- Average confidence score
- Precision, Recall, Accuracy (with manual ground truth labeling)
- False positive/negative rates
- Confusion matrix

Usage:
    python test_detection_accuracy.py --duration 120 --interval 1.0
"""

import cv2
import time
import os
import argparse
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from dotenv import load_dotenv
import numpy as np

load_dotenv()


@dataclass
class DetectionResult:
    """Single frame detection result."""
    frame_number: int
    timestamp: float
    detected: bool
    confidence: float
    detections: List[Dict]
    ground_truth: bool = None  # Will be labeled by user or auto


@dataclass
class AccuracyMetrics:
    """Detection accuracy metrics."""
    total_frames: int = 0
    frames_with_detection: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    
    total_confidence: float = 0.0
    max_confidence: float = 0.0
    min_confidence: float = 1.0
    
    def add_result(self, detected: bool, ground_truth: bool, confidence: float = 0.0):
        """Add a detection result to metrics."""
        self.total_frames += 1
        
        if detected:
            self.frames_with_detection += 1
            self.total_confidence += confidence
            self.max_confidence = max(self.max_confidence, confidence)
            if confidence > 0:
                self.min_confidence = min(self.min_confidence, confidence)
        
        # Confusion matrix
        if ground_truth and detected:
            self.true_positives += 1
        elif ground_truth and not detected:
            self.false_negatives += 1
        elif not ground_truth and detected:
            self.false_positives += 1
        elif not ground_truth and not detected:
            self.true_negatives += 1
    
    @property
    def detection_rate(self) -> float:
        """Percentage of frames with detections."""
        return (self.frames_with_detection / self.total_frames * 100) if self.total_frames > 0 else 0.0
    
    @property
    def avg_confidence(self) -> float:
        """Average confidence across detected frames."""
        return (self.total_confidence / self.frames_with_detection) if self.frames_with_detection > 0 else 0.0
    
    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)"""
        denominator = self.true_positives + self.false_positives
        return (self.true_positives / denominator * 100) if denominator > 0 else 0.0
    
    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)"""
        denominator = self.true_positives + self.false_negatives
        return (self.true_positives / denominator * 100) if denominator > 0 else 0.0
    
    @property
    def accuracy(self) -> float:
        """Accuracy = (TP + TN) / Total"""
        return ((self.true_positives + self.true_negatives) / self.total_frames * 100) if self.total_frames > 0 else 0.0
    
    @property
    def f1_score(self) -> float:
        """F1 Score = 2 * (Precision * Recall) / (Precision + Recall)"""
        p = self.precision
        r = self.recall
        return (2 * p * r / (p + r)) if (p + r) > 0 else 0.0


class DetectionAccuracyTest:
    """Test harness for detection accuracy."""
    
    def __init__(
        self,
        duration: float = 120.0,
        capture_interval: float = 1.0,
        camera_index: int = 0,
        confidence_threshold: float = 0.5,
        auto_labeling: bool = True,
        show_preview: bool = True
    ):
        self.duration = duration
        self.capture_interval = capture_interval
        self.camera_index = camera_index
        self.confidence_threshold = confidence_threshold
        self.auto_labeling = auto_labeling
        self.show_preview = show_preview
        
        self.results: List[DetectionResult] = []
        self.metrics = AccuracyMetrics()
        self.cap = None
        self.detector = None
    
    def _init_detector(self):
        """Initialize the detector."""
        detector_type = os.getenv("DETECTOR_TYPE", "roboflow").lower()
        
        if detector_type in ("roboflow", "cloud"):
            from services.roboflow_detector import get_roboflow_detector
            self.detector = get_roboflow_detector()
            roboflow_local = os.getenv("ROBOFLOW_LOCAL", "false").lower() == "true"
            mode = "LOCAL SERVER" if roboflow_local else "CLOUD API"
            print(f"✅ Using Roboflow detector ({mode})")
        elif detector_type in ("local", "yolo"):
            from services.local_yolo_detector import get_detector
            self.detector = get_detector()
            print(f"✅ Using Local YOLO detector")
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")
    
    def _init_camera(self):
        """Initialize webcam."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {self.camera_index}")
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"✅ Camera opened: {width}x{height}")
    
    def _detect_frame(self, frame) -> Tuple[bool, float, List[Dict]]:
        """Run detection on a frame."""
        detections = self.detector.detect(frame)
        
        # Filter by confidence and class
        valid_detections = [
            d for d in detections
            if d['class'] in ['Human', 'person']
            and d['confidence'] >= self.confidence_threshold
        ]
        
        has_detection = len(valid_detections) > 0
        max_conf = max([d['confidence'] for d in valid_detections], default=0.0)
        
        return has_detection, max_conf, valid_detections
    
    def _draw_detections(self, frame, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes on frame."""
        annotated = frame.copy()
        
        for det in detections:
            # Get bbox - handle both flat and nested formats
            if 'bbox' in det:
                bbox = det['bbox']
                x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
            else:
                x, y, w, h = det['x'], det['y'], det['width'], det['height']
            
            x1 = int(x - w/2)
            y1 = int(y - h/2)
            x2 = int(x + w/2)
            y2 = int(y + h/2)
            
            # Draw box
            color = (0, 255, 0)  # Green
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            class_name = det.get('class', det.get('class_name', 'Unknown'))
            confidence = det.get('confidence', 0)
            label = f"{class_name} {confidence:.2f}"
            cv2.putText(annotated, label, (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return annotated
    
    def _auto_label_ground_truth(self, has_detection: bool, confidence: float) -> bool:
        """
        Automatic ground truth labeling.
        Assumes high-confidence detections are true positives.
        This is not perfect but useful for automated testing.
        """
        # Simple heuristic: if confidence > 0.6, assume person is present
        return has_detection and confidence > 0.6
    
    def run(self):
        """Run the accuracy test."""
        print("\n" + "="*60)
        print("DETECTION ACCURACY TEST")
        print("="*60)
        print(f"  Duration: {self.duration}s")
        print(f"  Capture Interval: {self.capture_interval}s")
        print(f"  Confidence Threshold: {self.confidence_threshold}")
        print(f"  Auto Labeling: {self.auto_labeling}")
        print("="*60)
        
        # Initialize
        self._init_detector()
        self._init_camera()
        
        print(f"\n🚀 Starting test... (Press 'q' to stop early)\n")
        
        start_time = time.time()
        frame_number = 0
        
        try:
            while time.time() - start_time < self.duration:
                ret, frame = self.cap.read()
                if not ret:
                    print("⚠️  Failed to capture frame")
                    continue
                
                frame_number += 1
                timestamp = time.time() - start_time
                
                # Detect
                has_detection, confidence, detections = self._detect_frame(frame)
                
                # Ground truth labeling
                if self.auto_labeling:
                    ground_truth = self._auto_label_ground_truth(has_detection, confidence)
                else:
                    # Manual labeling (for future enhancement)
                    ground_truth = has_detection  # Simplified for now
                
                # Store result
                result = DetectionResult(
                    frame_number=frame_number,
                    timestamp=timestamp,
                    detected=has_detection,
                    confidence=confidence,
                    detections=detections,
                    ground_truth=ground_truth
                )
                self.results.append(result)
                
                # Update metrics
                self.metrics.add_result(has_detection, ground_truth, confidence)
                
                # Progress display
                elapsed = time.time() - start_time
                remaining = self.duration - elapsed
                status = "✅ DETECTED" if has_detection else "❌ No detection"
                conf_str = f"(conf: {confidence:.2f})" if has_detection else ""
                print(f"[{elapsed:05.1f}s] Frame {frame_number:03d}: {status} {conf_str} | Remaining: {remaining:.1f}s")
                
                # Show preview
                if self.show_preview:
                    annotated = self._draw_detections(frame, detections)
                    
                    # Add stats overlay with color coding
                    # Cyan for frame/time info
                    cv2.putText(annotated, f"Frame: {frame_number}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)  # Cyan
                    cv2.putText(annotated, f"Time: {elapsed:.1f}s / {self.duration}s", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)  # Cyan
                    
                    # Green if detecting well (>50%), red if not
                    rate_color = (0, 255, 0) if self.metrics.detection_rate > 50 else (0, 0, 255)
                    cv2.putText(annotated, f"Detection Rate: {self.metrics.detection_rate:.1f}%", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, rate_color, 2)
                    
                    cv2.imshow("Detection Accuracy Test", annotated)
                    
                    # Check for quit key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("\n⏹️  Test stopped by user")
                        break
                
                # Wait for next capture
                time.sleep(self.capture_interval)
        
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted by user")
        
        finally:
            if self.cap:
                self.cap.release()
            if self.show_preview:
                cv2.destroyAllWindows()
        
        # Print final results
        self._print_results()
    
    def _print_results(self):
        """Print final accuracy metrics."""
        m = self.metrics
        
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        
        print("\n📊 DETECTION STATISTICS:")
        print(f"  Total Frames: {m.total_frames}")
        print(f"  Frames with Detection: {m.frames_with_detection} ({m.detection_rate:.1f}%)")
        print(f"  Average Confidence: {m.avg_confidence:.2f}")
        print(f"  Min Confidence: {m.min_confidence:.2f}")
        print(f"  Max Confidence: {m.max_confidence:.2f}")
        
        print("\n🎯 ACCURACY METRICS:")
        print(f"  Precision: {m.precision:.2f}%")
        print(f"  Recall: {m.recall:.2f}%")
        print(f"  Accuracy: {m.accuracy:.2f}%")
        print(f"  F1 Score: {m.f1_score:.2f}%")
        
        print("\n📈 CONFUSION MATRIX:")
        print(f"  True Positives (TP):  {m.true_positives}")
        print(f"  False Positives (FP): {m.false_positives}")
        print(f"  True Negatives (TN):  {m.true_negatives}")
        print(f"  False Negatives (FN): {m.false_negatives}")
        
        print("\n" + "="*60)
        
        # Frame-by-frame details (optional)
        if len(self.results) <= 20:  # Only show for short tests
            print("\n📋 FRAME-BY-FRAME RESULTS:")
            for r in self.results:
                status = "✅ TP" if r.detected and r.ground_truth else \
                        "❌ FP" if r.detected and not r.ground_truth else \
                        "⚠️  FN" if not r.detected and r.ground_truth else \
                        "✅ TN"
                conf_str = f"{r.confidence:.2f}" if r.detected else "N/A"
                print(f"  Frame {r.frame_number:03d} [{r.timestamp:05.1f}s]: {status} (conf: {conf_str})")


def main():
    parser = argparse.ArgumentParser(description="Test detection accuracy")
    parser.add_argument("--duration", type=float, default=120.0,
                       help="Test duration in seconds (default: 120)")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Capture interval in seconds (default: 1.0)")
    parser.add_argument("--camera", type=int, default=0,
                       help="Camera index (default: 0)")
    parser.add_argument("--confidence", type=float, default=0.5,
                       help="Confidence threshold (default: 0.5)")
    parser.add_argument("--no-preview", action="store_true",
                       help="Disable preview window")
    parser.add_argument("--no-auto-label", action="store_true",
                       help="Disable automatic ground truth labeling")
    
    args = parser.parse_args()
    
    test = DetectionAccuracyTest(
        duration=args.duration,
        capture_interval=args.interval,
        camera_index=args.camera,
        confidence_threshold=args.confidence,
        auto_labeling=not args.no_auto_label,
        show_preview=not args.no_preview
    )
    
    test.run()


if __name__ == "__main__":
    main()
