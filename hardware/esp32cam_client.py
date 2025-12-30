"""
ESP32-CAM Client - Captures frames from ESP32-CAM

Connects to ESP32-CAM HTTP endpoint and captures JPEG frames
for intruder detection processing.
"""

import time
import threading
import requests
from typing import Optional, Callable, Any
from io import BytesIO

from config import ESP32CamConfig


class ESP32CamClient:
    """
    Captures frames from ESP32-CAM via HTTP.
    
    Supports both:
    - Single capture mode (/capture endpoint)
    - MJPEG stream mode (/stream endpoint)
    """
    
    def __init__(
        self,
        config: Optional[ESP32CamConfig] = None,
        on_frame: Optional[Callable[[bytes, float], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.config = config or ESP32CamConfig()
        self.on_frame = on_frame
        self.on_error = on_error
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[bytes] = None
        self._latest_timestamp: float = 0
        self._lock = threading.Lock()
        self._capture_count = 0
        self._error_count = 0
    
    def _capture_single(self) -> Optional[bytes]:
        """Capture a single frame from ESP32-CAM /capture endpoint."""
        try:
            response = requests.get(
                self.config.stream_url,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"[esp32cam] ⚠️ HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            self._error_count += 1
            if self._error_count % 10 == 1:  # Log every 10th error
                print(f"[esp32cam] ❌ Capture error: {e}")
            return None
    
    def _capture_loop(self):
        """Main capture loop (runs in background thread)."""
        print(f"[esp32cam] 🎥 Starting capture loop (interval={self.config.capture_interval}s)")
        print(f"[esp32cam] 📡 URL: {self.config.stream_url}")
        
        consecutive_errors = 0
        
        while self._running:
            loop_start = time.time()
            
            # Capture frame
            frame_bytes = self._capture_single()
            
            if frame_bytes:
                consecutive_errors = 0
                self._capture_count += 1
                timestamp = time.time()
                
                with self._lock:
                    self._latest_frame = frame_bytes
                    self._latest_timestamp = timestamp
                
                # Log periodically
                if self._capture_count % 20 == 0:
                    print(f"[esp32cam] 📸 Captured {self._capture_count} frames, "
                          f"last size: {len(frame_bytes)} bytes")
                
                # Callback
                if self.on_frame:
                    try:
                        self.on_frame(frame_bytes, timestamp)
                    except Exception as e:
                        print(f"[esp32cam] ⚠️ Callback error: {e}")
            else:
                consecutive_errors += 1
                
                # Exponential backoff on errors
                if consecutive_errors >= self.config.max_retries:
                    print(f"[esp32cam] ⚠️ {consecutive_errors} consecutive errors, waiting...")
                    time.sleep(self.config.retry_delay * min(consecutive_errors, 10))
            
            # Wait for next capture
            elapsed = time.time() - loop_start
            sleep_time = max(0, self.config.capture_interval - elapsed)
            
            sleep_end = time.time() + sleep_time
            while self._running and time.time() < sleep_end:
                time.sleep(0.1)
        
        print("[esp32cam] 🛑 Capture loop stopped")
    
    def start(self) -> bool:
        """Start the camera client."""
        if self._running:
            return True
        
        # Test connection first
        print(f"[esp32cam] Testing connection to {self.config.stream_url}...")
        test_frame = self._capture_single()
        if test_frame:
            print(f"[esp32cam] ✅ Connection OK, frame size: {len(test_frame)} bytes")
        else:
            print("[esp32cam] ⚠️ Initial connection failed, will retry...")
        
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        
        print("[esp32cam] ✅ Started")
        return True
    
    def stop(self):
        """Stop the camera client."""
        if not self._running:
            return
        
        print("[esp32cam] Stopping...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        
        print("[esp32cam] ✅ Stopped")
    
    def get_latest_frame(self) -> tuple:
        """Get the most recent captured frame."""
        with self._lock:
            return self._latest_frame, self._latest_timestamp
    
    def capture_now(self) -> Optional[bytes]:
        """Capture a frame immediately (blocking)."""
        return self._capture_single()
    
    def get_stats(self) -> dict:
        """Get client statistics."""
        return {
            "running": self._running,
            "capture_count": self._capture_count,
            "error_count": self._error_count,
            "url": self.config.stream_url,
        }
    
    @property
    def is_running(self) -> bool:
        return self._running
