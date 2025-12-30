"""
Action Controller - Controls GPIO relays on Raspberry Pi

Handles:
- Fan relay control
- Buzzer activation
- Light control
- Any other GPIO-connected actuators

Platform-aware: Uses mock GPIO on Windows for testing.
"""

import time
import threading
from typing import Optional, Dict, Callable
import platform

from config import ActionControllerConfig


# Platform-aware GPIO import
if platform.system() == "Linux":
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False
        print("[action_controller] ⚠️ RPi.GPIO not available, using mock")
else:
    GPIO_AVAILABLE = False


class MockGPIO:
    """Mock GPIO for Windows testing."""
    BCM = "BCM"
    OUT = "OUT"
    HIGH = 1
    LOW = 0
    
    _states = {}
    
    @classmethod
    def setmode(cls, mode):
        print(f"[MockGPIO] setmode({mode})")
    
    @classmethod
    def setup(cls, pin, direction):
        print(f"[MockGPIO] setup(pin={pin}, dir={direction})")
        cls._states[pin] = cls.LOW
    
    @classmethod
    def output(cls, pin, state):
        cls._states[pin] = state
        state_str = "HIGH" if state == cls.HIGH else "LOW"
        print(f"[MockGPIO] output(pin={pin}, state={state_str})")
    
    @classmethod
    def input(cls, pin):
        return cls._states.get(pin, cls.LOW)
    
    @classmethod
    def cleanup(cls):
        print("[MockGPIO] cleanup()")
        cls._states.clear()


# Use real GPIO on Pi, mock on Windows
if GPIO_AVAILABLE:
    from RPi import GPIO
else:
    GPIO = MockGPIO


class ActionController:
    """
    Controls GPIO relays and actuators.
    
    Thread-safe, supports timed actions (e.g., buzzer for 5 seconds).
    """
    
    def __init__(
        self,
        config: Optional[ActionControllerConfig] = None,
        on_state_change: Optional[Callable[[str, bool], None]] = None,
    ):
        self.config = config or ActionControllerConfig()
        self.on_state_change = on_state_change
        
        self._initialized = False
        self._states: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._timers: Dict[str, threading.Timer] = {}
    
    def initialize(self) -> bool:
        """Initialize GPIO pins."""
        if self._initialized:
            return True
        
        try:
            GPIO.setmode(GPIO.BCM)
            
            for name, pin in self.config.relay_pins.items():
                GPIO.setup(pin, GPIO.OUT)
                initial = self.config.initial_states.get(name, False)
                self._set_pin(name, initial)
                self._states[name] = initial
                print(f"[action_controller] Pin {pin} ({name}) initialized")
            
            self._initialized = True
            print("[action_controller] ✅ GPIO initialized")
            return True
            
        except Exception as e:
            print(f"[action_controller] ❌ GPIO init failed: {e}")
            return False
    
    def _set_pin(self, name: str, state: bool):
        """Set a GPIO pin state (handles active-low logic)."""
        pin = self.config.relay_pins.get(name)
        if pin is None:
            return
        
        # Active-low relays: HIGH = OFF, LOW = ON
        if self.config.active_low:
            gpio_state = GPIO.LOW if state else GPIO.HIGH
        else:
            gpio_state = GPIO.HIGH if state else GPIO.LOW
        
        GPIO.output(pin, gpio_state)
    
    def set_state(self, name: str, state: bool) -> bool:
        """
        Set an actuator state.
        
        Args:
            name: Actuator name (fan, buzzer, light)
            state: True for ON, False for OFF
        
        Returns:
            True if successful
        """
        if not self._initialized:
            self.initialize()
        
        if name not in self.config.relay_pins:
            print(f"[action_controller] ⚠️ Unknown actuator: {name}")
            return False
        
        with self._lock:
            # Cancel any pending timer for this actuator
            if name in self._timers:
                self._timers[name].cancel()
                del self._timers[name]
            
            self._set_pin(name, state)
            self._states[name] = state
        
        state_str = "ON" if state else "OFF"
        print(f"[action_controller] 🔌 {name.upper()} → {state_str}")
        
        if self.on_state_change:
            try:
                self.on_state_change(name, state)
            except Exception as e:
                print(f"[action_controller] ⚠️ Callback error: {e}")
        
        return True
    
    def set_timed(self, name: str, state: bool, duration: float) -> bool:
        """
        Set an actuator state for a specified duration.
        
        Args:
            name: Actuator name
            state: State to set
            duration: Seconds to hold the state before reverting
        
        Returns:
            True if successful
        """
        if not self.set_state(name, state):
            return False
        
        # Schedule revert
        def revert():
            with self._lock:
                if name in self._timers:
                    del self._timers[name]
            self.set_state(name, not state)
        
        timer = threading.Timer(duration, revert)
        timer.daemon = True
        
        with self._lock:
            if name in self._timers:
                self._timers[name].cancel()
            self._timers[name] = timer
        
        timer.start()
        print(f"[action_controller] ⏱️ {name.upper()} will revert in {duration}s")
        
        return True
    
    def trigger_alarm(self, duration: float = 5.0):
        """Trigger buzzer alarm for specified duration."""
        return self.set_timed("buzzer", True, duration)
    
    def get_state(self, name: str) -> Optional[bool]:
        """Get current state of an actuator."""
        with self._lock:
            return self._states.get(name)
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get all actuator states."""
        with self._lock:
            return self._states.copy()
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        print("[action_controller] Cleaning up...")
        
        # Cancel all timers
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
        
        # Turn off all actuators
        for name in self.config.relay_pins:
            self.set_state(name, False)
        
        GPIO.cleanup()
        self._initialized = False
        
        print("[action_controller] ✅ Cleanup complete")
