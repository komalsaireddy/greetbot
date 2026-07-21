"""
GreetBot Servo Controller
==========================
Controls pan/tilt servos to track faces using Raspberry Pi GPIO.
Runs in no-op mode on non-Pi hardware (dev machines) so the rest
of the system works without physical hardware attached.
"""

import threading
import time
from typing import Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)

# ── GPIO Pin Configuration ────────────────────────────────────────────────────

PAN_PIN   = 12   # BCM pin for horizontal (pan) servo
TILT_PIN  = 13   # BCM pin for vertical (tilt) servo

# Servo angle limits
PAN_MIN, PAN_MAX   = 30, 150   # degrees
TILT_MIN, TILT_MAX = 50, 120   # degrees
PAN_CENTER  = 90
TILT_CENTER = 80

# PWM frequency
PWM_FREQ = 50   # Hz (standard for hobby servos)

# Angle → duty cycle conversion for standard servos
# 0° = 2.5% duty, 90° = 7.5%, 180° = 12.5%
def _angle_to_duty(angle: float) -> float:
    return 2.5 + (angle / 180.0) * 10.0


class ServoController:
    """
    Pan/tilt servo controller for face tracking.

    On non-Raspberry-Pi hardware, all methods are no-ops so the
    rest of the system works unmodified on development machines.

    Parameters
    ----------
    pan_pin:
        BCM GPIO pin for the pan (horizontal) servo.
    tilt_pin:
        BCM GPIO pin for the tilt (vertical) servo.
    smoothing:
        Lerp factor [0, 1] for smooth movement. Higher = faster.
    """

    def __init__(
        self,
        pan_pin: int = PAN_PIN,
        tilt_pin: int = TILT_PIN,
        smoothing: float = 0.06,
    ) -> None:
        self._available: bool = False
        self._pan_angle: float = float(PAN_CENTER)
        self._tilt_angle: float = float(TILT_CENTER)
        self._target_pan: float = float(PAN_CENTER)
        self._target_tilt: float = float(TILT_CENTER)
        self._smoothing = smoothing

        self._pan_pwm  = None
        self._tilt_pwm = None
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False

        try:
            import RPi.GPIO as GPIO  # type: ignore[import]

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            GPIO.setup(pan_pin,  GPIO.OUT)
            GPIO.setup(tilt_pin, GPIO.OUT)

            self._pan_pwm  = GPIO.PWM(pan_pin,  PWM_FREQ)
            self._tilt_pwm = GPIO.PWM(tilt_pin, PWM_FREQ)

            self._pan_pwm.start(_angle_to_duty(PAN_CENTER))
            self._tilt_pwm.start(_angle_to_duty(TILT_CENTER))

            self._available = True
            self._running = True

            self._thread = threading.Thread(
                target=self._smooth_loop,
                daemon=True,
                name="ServoThread",
            )
            self._thread.start()

            log.info("ServoController ready (GPIO active)")

        except ImportError:
            log.info("RPi.GPIO not available — servo running in no-op mode")
        except Exception as exc:
            log.warning(f"Servo init failed: {exc} — running in no-op mode")

    # ── Public API ────────────────────────────────────────────────────────────

    def track_face(
        self,
        face_cx: int,
        face_cy: int,
        frame_w: int,
        frame_h: int,
    ) -> None:
        """
        Point the camera toward a detected face center.

        Converts normalized face position to servo angles.

        Parameters
        ----------
        face_cx, face_cy:
            Face centroid in camera pixel coordinates.
        frame_w, frame_h:
            Camera frame dimensions.
        """
        if not self._available:
            return

        # Normalize face position to [-1, 1]
        norm_x = (face_cx / frame_w - 0.5) * 2.0
        norm_y = (face_cy / frame_h - 0.5) * 2.0

        # Map to servo angles
        pan_range  = PAN_MAX  - PAN_MIN
        tilt_range = TILT_MAX - TILT_MIN

        target_pan  = PAN_CENTER  - norm_x * pan_range  * 0.4
        target_tilt = TILT_CENTER + norm_y * tilt_range * 0.3

        self._target_pan  = max(PAN_MIN,  min(PAN_MAX,  target_pan))
        self._target_tilt = max(TILT_MIN, min(TILT_MAX, target_tilt))

    def center(self) -> None:
        """Return both servos to the center position."""
        self._target_pan  = float(PAN_CENTER)
        self._target_tilt = float(TILT_CENTER)

    def stop(self) -> None:
        """Stop the servo control thread and clean up GPIO."""
        self._running = False
        if not self._available:
            return

        try:
            if self._pan_pwm:
                self._pan_pwm.stop()
            if self._tilt_pwm:
                self._tilt_pwm.stop()
            import RPi.GPIO as GPIO
            GPIO.cleanup()
            log.info("ServoController stopped")
        except Exception as exc:
            log.error(f"Servo cleanup error: {exc}")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _smooth_loop(self) -> None:
        """Background thread: lerp current angles toward targets and write PWM."""
        while self._running:
            # Smooth interpolation
            self._pan_angle  += (self._target_pan  - self._pan_angle)  * self._smoothing
            self._tilt_angle += (self._target_tilt - self._tilt_angle) * self._smoothing

            try:
                self._pan_pwm.ChangeDutyCycle(_angle_to_duty(self._pan_angle))
                self._tilt_pwm.ChangeDutyCycle(_angle_to_duty(self._tilt_angle))
            except Exception:
                pass

            time.sleep(0.02)   # 50 Hz update rate
