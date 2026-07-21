"""
GreetBot Avatar Mouth
======================
Renders an animated mouth that shows speaking motion, smiling, and
neutral expressions synchronized with TTS output.
"""

import math
import time

import pygame

from avatar.animations import Animator, PulseAnimator, ease_in_out_sine


# ── Colors ────────────────────────────────────────────────────────────────────

MOUTH_COLOR      = (30,  40,  60)
MOUTH_INNER      = (15,  10,  20)
LIPS_COLOR       = (80, 100, 160)
TEETH_COLOR      = (240, 245, 255)


class MouthState:
    NEUTRAL = "NEUTRAL"
    SMILE   = "SMILE"
    SPEAK   = "SPEAK"
    OPEN    = "OPEN"


class Mouth:
    """
    Animated mouth renderer.

    Supports neutral, smiling, and speaking (jaw-flap) states.
    When speaking, the mouth opens and closes in a randomized pattern
    that mimics natural speech rhythm.

    Parameters
    ----------
    surface:
        pygame Surface to draw onto.
    center:
        (x, y) pixel position of the mouth center.
    width:
        Mouth width in pixels.
    """

    def __init__(
        self,
        surface: pygame.Surface,
        center: tuple[int, int] = (400, 430),
        width: int = 180,
    ) -> None:
        self._surface = surface
        self._center = center
        self._width = width
        self._height_base = 30

        self._state: str = MouthState.NEUTRAL

        # Smile curve amount (0=flat, 1=big smile)
        self._smile: float = 0.0
        self._smile_anim: Animator = Animator(0.0, 0.0, 0.3, ease_in_out_sine)

        # Jaw open amount (0=closed, 1=fully open)
        self._jaw_open: float = 0.0
        self._speak_pulse: PulseAnimator = PulseAnimator(0.1, 0.9, 3.5)

        self._is_speaking: bool = False

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """
        Change the mouth expression.

        Parameters
        ----------
        state:
            One of the ``MouthState`` constants.
        """
        if state == self._state:
            return

        prev_smile = self._smile_anim.tick()
        self._state = state

        targets = {
            MouthState.NEUTRAL: 0.0,
            MouthState.SMILE:   0.8,
            MouthState.SPEAK:   0.2,
            MouthState.OPEN:    1.0,
        }
        self._smile_anim = Animator(prev_smile, targets.get(state, 0.0), 0.35, ease_in_out_sine)
        self._is_speaking = (state == MouthState.SPEAK)

    def set_speaking(self, speaking: bool) -> None:
        """
        Toggle speaking animation.

        Parameters
        ----------
        speaking:
            If True, animate the jaw open/close. If False, close mouth.
        """
        if speaking:
            self.set_state(MouthState.SPEAK)
        else:
            self.set_state(MouthState.SMILE if self._smile > 0.3 else MouthState.NEUTRAL)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Draw the mouth onto the surface. Call every frame."""
        self._smile = self._smile_anim.tick()

        if self._is_speaking:
            self._jaw_open = self._speak_pulse.tick()
        else:
            # Lerp jaw closed
            self._jaw_open += (0.0 - self._jaw_open) * 0.15

        self._draw_mouth()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _draw_mouth(self) -> None:
        cx, cy = self._center
        w = self._width
        h = self._height_base

        # ── Jaw opening ───────────────────────────────────────────────────────
        jaw = int(self._jaw_open * 35)

        # ── Outline / lips ────────────────────────────────────────────────────
        # Smile curve displaces corners upward
        corner_lift = int(self._smile * 28)

        # Bezier approximation using points + pygame.draw.lines
        # Left corner, center-bottom (with jaw), right corner
        left  = (cx - w // 2, cy + corner_lift)
        right = (cx + w // 2, cy + corner_lift)
        mid_b = (cx, cy + h + jaw)
        mid_t = (cx, cy - jaw // 2)

        # Draw filled mouth shape as a polygon
        mouth_poly = self._bezier_mouth(left, right, mid_b, mid_t, self._smile, jaw)
        if len(mouth_poly) >= 3:
            pygame.draw.polygon(self._surface, MOUTH_INNER, mouth_poly)
            pygame.draw.polygon(self._surface, LIPS_COLOR, mouth_poly, 4)

        # Teeth strip when mouth is open
        if jaw > 5:
            tooth_rect = pygame.Rect(
                cx - w // 2 + 15,
                cy - jaw // 2 + 4,
                w - 30,
                max(3, jaw // 3)
            )
            pygame.draw.rect(self._surface, TEETH_COLOR, tooth_rect, border_radius=4)

    def _bezier_mouth(
        self,
        left: tuple[int, int],
        right: tuple[int, int],
        mid_b: tuple[int, int],
        mid_t: tuple[int, int],
        smile: float,
        jaw: int,
    ) -> list[tuple[int, int]]:
        """Generate polygon points approximating a mouth shape."""
        points = []
        steps = 20

        # Top lip: flat curve from left to right
        for i in range(steps + 1):
            t = i / steps
            # Quadratic bezier: left → mid_t → right
            x = (1 - t) ** 2 * left[0] + 2 * (1 - t) * t * mid_t[0] + t ** 2 * right[0]
            y = (1 - t) ** 2 * left[1] + 2 * (1 - t) * t * mid_t[1] + t ** 2 * right[1]
            points.append((int(x), int(y)))

        # Bottom lip: smile curve from right to left
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * right[0] + 2 * (1 - t) * t * mid_b[0] + t ** 2 * left[0]
            y = (1 - t) ** 2 * right[1] + 2 * (1 - t) * t * mid_b[1] + t ** 2 * left[1]
            points.append((int(x), int(y)))

        return points
