"""
GreetBot Avatar Animations
===========================
Easing and interpolation utilities for smooth avatar animations.
All avatar components use these functions for fluid state transitions.
"""

import math
import time
from typing import Callable, Generator


# ── Easing Functions ──────────────────────────────────────────────────────────

def ease_in_out_quad(t: float) -> float:
    """Smooth accelerate-decelerate easing. t in [0, 1]."""
    if t < 0.5:
        return 2.0 * t * t
    return -1.0 + (4.0 - 2.0 * t) * t


def ease_out_cubic(t: float) -> float:
    """Decelerating ease. t in [0, 1]."""
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t: float) -> float:
    """Accelerating ease. t in [0, 1]."""
    return t ** 3


def ease_in_out_sine(t: float) -> float:
    """Sine-based smooth easing. t in [0, 1]."""
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def ease_bounce_out(t: float) -> float:
    """Bouncing deceleration effect. t in [0, 1]."""
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


# ── Animator Class ────────────────────────────────────────────────────────────

class Animator:
    """
    Interpolates a value from *start* to *end* over *duration* seconds.

    Use by calling ``tick()`` every frame with the current time to get
    the interpolated value.

    Parameters
    ----------
    start:
        Starting value.
    end:
        Target value.
    duration:
        Animation duration in seconds.
    easing:
        Easing function (takes t ∈ [0,1], returns value ∈ [0,1]).
    """

    def __init__(
        self,
        start: float,
        end: float,
        duration: float,
        easing: Callable[[float], float] = ease_in_out_quad,
    ) -> None:
        self._start = start
        self._end = end
        self._duration = max(duration, 0.001)
        self._easing = easing
        self._begin_time: float = time.time()

    def tick(self) -> float:
        """
        Get the current interpolated value.

        Returns
        -------
        float
            Value between *start* and *end*, clamped to [start, end].
        """
        elapsed = time.time() - self._begin_time
        t = min(elapsed / self._duration, 1.0)
        eased_t = self._easing(t)
        return self._start + (self._end - self._start) * eased_t

    @property
    def done(self) -> bool:
        """True when the animation has completed."""
        return (time.time() - self._begin_time) >= self._duration

    def restart(self, start: float = None, end: float = None) -> None:
        """Restart the animation, optionally with new start/end values."""
        if start is not None:
            self._start = start
        if end is not None:
            self._end = end
        self._begin_time = time.time()

    @property
    def value(self) -> float:
        """Alias for tick()."""
        return self.tick()

    @property
    def final(self) -> float:
        """The target end value."""
        return self._end


class PulseAnimator:
    """
    Continuously oscillates a value between *low* and *high*
    using a sine wave.

    Parameters
    ----------
    low:
        Minimum value.
    high:
        Maximum value.
    speed:
        Oscillations per second.
    """

    def __init__(
        self,
        low: float = 0.0,
        high: float = 1.0,
        speed: float = 1.0,
    ) -> None:
        self._low = low
        self._high = high
        self._speed = speed
        self._start = time.time()

    def tick(self) -> float:
        """Return the current pulsed value."""
        t = (time.time() - self._start) * self._speed
        sine = (math.sin(2 * math.pi * t) + 1.0) / 2.0  # [0, 1]
        return self._low + (self._high - self._low) * sine
