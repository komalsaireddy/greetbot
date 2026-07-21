"""
GreetBot Avatar Eyes
=====================
Renders animated eyes with blinking, gaze direction tracking,
and emotion-driven expressions. Designed to run at 60 FPS with pygame.
"""

import math
import random
import time

import pygame

from avatar.animations import Animator, ease_in_out_quad, ease_out_cubic


# ── Color Palette ─────────────────────────────────────────────────────────────

EYE_WHITE       = (220, 230, 240)
EYE_IRIS_BASE   = (40,  120, 220)
EYE_PUPIL       = (10,   20,  30)
EYE_HIGHLIGHT   = (255, 255, 255)
EYE_OUTLINE     = (30,   40,  60)
EYELID_COLOR    = (20,   30,  55)   # Same as background


class EyeState:
    OPEN      = "OPEN"
    BLINK     = "BLINK"
    SQUINT    = "SQUINT"    # Happy
    WIDE      = "WIDE"      # Surprised
    HALF      = "HALF"      # Thoughtful / sleepy


class Eyes:
    """
    Renders a pair of expressive animated robot eyes.

    Parameters
    ----------
    surface:
        The pygame surface to draw onto.
    left_center:
        (x, y) pixel center of the left eye.
    right_center:
        (x, y) pixel center of the right eye.
    radius:
        Base eye radius in pixels.
    """

    def __init__(
        self,
        surface: pygame.Surface,
        left_center: tuple[int, int] = (250, 280),
        right_center: tuple[int, int] = (550, 280),
        radius: int = 80,
    ) -> None:
        self._surface = surface
        self._left_center = left_center
        self._right_center = right_center
        self._radius = radius

        # Blink state
        self._blink_progress: float = 0.0   # 0=open, 1=fully closed
        self._is_blinking: bool = False
        self._blink_anim: Animator = Animator(0, 0, 0.1)
        self._next_blink: float = time.time() + random.uniform(3.0, 6.0)

        # Gaze direction [-1, 1] in x and y
        self._gaze_x: float = 0.0
        self._gaze_y: float = 0.0
        self._target_gaze_x: float = 0.0
        self._target_gaze_y: float = 0.0

        # Expression state
        self._state: str = EyeState.OPEN
        self._squint_anim: Animator = Animator(0.0, 0.0, 0.3)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """
        Change the eye expression state.

        Parameters
        ----------
        state:
            One of the ``EyeState`` constants.
        """
        if state == self._state:
            return
        self._state = state
        target_squint = {
            EyeState.OPEN:      0.0,
            EyeState.BLINK:     1.0,
            EyeState.SQUINT:    0.5,
            EyeState.WIDE:     -0.2,
            EyeState.HALF:      0.4,
        }.get(state, 0.0)
        self._squint_anim = Animator(self._squint_anim.tick(), target_squint, 0.3)

    def set_gaze(self, x: float, y: float) -> None:
        """
        Set gaze target direction.

        Parameters
        ----------
        x, y:
            Normalized gaze direction, each in [-1.0, 1.0].
        """
        self._target_gaze_x = max(-1.0, min(1.0, x))
        self._target_gaze_y = max(-1.0, min(1.0, y))

    def set_gaze_toward(
        self,
        face_cx: int,
        face_cy: int,
        frame_w: int,
        frame_h: int,
    ) -> None:
        """
        Point gaze toward a detected face center in the camera frame.

        Parameters
        ----------
        face_cx, face_cy:
            Face centroid in camera pixel coordinates.
        frame_w, frame_h:
            Camera frame dimensions.
        """
        # Normalize to [-1, 1] (invert X because camera mirror)
        nx = -(face_cx / frame_w - 0.5) * 2.0
        ny = (face_cy / frame_h - 0.5) * 2.0
        self.set_gaze(nx, ny)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Draw the eyes onto the surface. Call every frame."""
        self._update_blink()
        self._smooth_gaze()

        squint = self._squint_anim.tick()
        blink = self._blink_progress

        self._draw_eye(self._left_center,  squint, blink, side="left")
        self._draw_eye(self._right_center, squint, blink, side="right")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _update_blink(self) -> None:
        now = time.time()

        if not self._is_blinking and now >= self._next_blink:
            self._is_blinking = True
            self._blink_anim = Animator(0.0, 1.0, 0.07, ease_out_cubic)

        if self._is_blinking:
            p = self._blink_anim.tick()
            if self._blink_anim.done and self._blink_anim.final == 1.0:
                # Start opening
                self._blink_anim = Animator(1.0, 0.0, 0.12, ease_out_cubic)
            elif self._blink_anim.done and self._blink_anim.final == 0.0:
                self._is_blinking = False
                self._blink_progress = 0.0
                self._next_blink = now + random.uniform(3.0, 7.0)
                return
            self._blink_progress = self._blink_anim.tick()
        else:
            self._blink_progress = 0.0

    def _smooth_gaze(self) -> None:
        """Lerp current gaze toward target for smooth movement."""
        speed = 0.08
        self._gaze_x += (self._target_gaze_x - self._gaze_x) * speed
        self._gaze_y += (self._target_gaze_y - self._gaze_y) * speed

    def _draw_eye(
        self,
        center: tuple[int, int],
        squint: float,
        blink: float,
        side: str,
    ) -> None:
        """Render a single eye."""
        cx, cy = center
        r = self._radius

        # ── White of eye ──────────────────────────────────────────────────────
        pygame.draw.ellipse(
            self._surface, EYE_WHITE,
            (cx - r, cy - r, r * 2, r * 2)
        )
        pygame.draw.ellipse(
            self._surface, EYE_OUTLINE,
            (cx - r, cy - r, r * 2, r * 2),
            3
        )

        # ── Iris ──────────────────────────────────────────────────────────────
        iris_r = int(r * 0.55)
        gaze_offset_x = int(self._gaze_x * r * 0.25)
        gaze_offset_y = int(self._gaze_y * r * 0.20)

        iris_cx = cx + gaze_offset_x
        iris_cy = cy + gaze_offset_y

        # Clamp iris within white
        max_off = r - iris_r - 3
        iris_cx = cx + max(-max_off, min(max_off, gaze_offset_x))
        iris_cy = cy + max(-max_off, min(max_off, gaze_offset_y))

        pygame.draw.circle(self._surface, EYE_IRIS_BASE, (iris_cx, iris_cy), iris_r)

        # Pupil
        pupil_r = int(iris_r * 0.45)
        pygame.draw.circle(self._surface, EYE_PUPIL, (iris_cx, iris_cy), pupil_r)

        # Highlight
        h_off = int(iris_r * 0.3)
        pygame.draw.circle(
            self._surface, EYE_HIGHLIGHT,
            (iris_cx - h_off, iris_cy - h_off),
            int(iris_r * 0.18)
        )

        # ── Eyelid (blink + squint) ───────────────────────────────────────────
        # Effective closure = blink + squint
        closure = max(0.0, min(1.0, blink + squint))

        if closure > 0.01:
            lid_height = int(r * 2 * closure) + 2
            lid_rect = pygame.Rect(cx - r - 2, cy - r - 2, r * 2 + 4, lid_height)
            # Clip to eye bounding box
            clip = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
            pygame.draw.rect(self._surface, EYELID_COLOR, lid_rect.clip(clip))

            # Bottom lid for squint
            if squint > 0.1:
                bot_lid_h = int(r * 2 * (squint * 0.5))
                bot_rect = pygame.Rect(
                    cx - r - 2,
                    cy + r - bot_lid_h,
                    r * 2 + 4,
                    bot_lid_h + 2,
                )
                pygame.draw.rect(self._surface, EYELID_COLOR, bot_rect.clip(clip))
