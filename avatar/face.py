"""
GreetBot Avatar Face
=====================
Main avatar compositor — assembles eyes + mouth onto a robot face
and manages a pygame window running in a background thread.

The avatar displays emotion states and reacts to speech in real-time.
"""

import threading
import time
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)


# ── Colors ────────────────────────────────────────────────────────────────────

BG_COLOR          = (14,  18,  38)   # Dark navy
FACE_COLOR        = (22,  30,  60)   # Slightly lighter navy
FACE_OUTLINE      = (60,  90, 160)   # Blue outline
PANEL_COLOR       = (18,  25,  50)   # Dark panel
ACCENT            = (50, 120, 255)   # Bright blue accent
TEXT_COLOR        = (180, 200, 240)  # Soft white-blue
STATUS_COLOR      = (100, 180, 100)  # Green for status text
LISTENING_COLOR   = (255, 180,  50)  # Amber for listening indicator
SPEAKING_COLOR    = (80,  160, 255)  # Blue for speaking indicator


# ── Emotion → Expression Mapping ──────────────────────────────────────────────

from brain.emotion import Emotion
from avatar.eyes import EyeState
from avatar.mouth import MouthState

_EMOTION_TO_EYE = {
    Emotion.NEUTRAL:    EyeState.OPEN,
    Emotion.HAPPY:      EyeState.SQUINT,
    Emotion.CURIOUS:    EyeState.WIDE,
    Emotion.THOUGHTFUL: EyeState.HALF,
    Emotion.SURPRISED:  EyeState.WIDE,
    Emotion.SAD:        EyeState.HALF,
    Emotion.FRUSTRATED: EyeState.OPEN,
}

_EMOTION_TO_MOUTH = {
    Emotion.NEUTRAL:    MouthState.NEUTRAL,
    Emotion.HAPPY:      MouthState.SMILE,
    Emotion.CURIOUS:    MouthState.OPEN,
    Emotion.THOUGHTFUL: MouthState.NEUTRAL,
    Emotion.SURPRISED:  MouthState.OPEN,
    Emotion.SAD:        MouthState.NEUTRAL,
    Emotion.FRUSTRATED: MouthState.NEUTRAL,
}


class AvatarFace:
    """
    GreetBot's animated robot face displayed in a pygame window.

    Runs in a dedicated background thread to avoid blocking the main loop.
    Communicates with other modules through thread-safe property setters.

    Parameters
    ----------
    width:
        Window width in pixels.
    height:
        Window height in pixels.
    fps:
        Target frames per second.
    title:
        Window title.
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        fps: int = 60,
        title: str = "GreetBot",
    ) -> None:
        self._width = width
        self._height = height
        self._fps = fps
        self._title = title

        # Shared state (thread-safe with GIL for simple types)
        self._emotion: str = Emotion.NEUTRAL
        self._is_speaking: bool = False
        self._is_listening: bool = False
        self._status_text: str = "Initializing..."
        self._person_name: str = ""
        self._running: bool = False

        # Gaze target from vision
        self._gaze_x: float = 0.0
        self._gaze_y: float = 0.0

        self._thread: Optional[threading.Thread] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def set_emotion(self, emotion: str) -> None:
        """Set the avatar's current emotion expression."""
        self._emotion = emotion

    def set_speaking(self, speaking: bool) -> None:
        """Toggle speaking animation on the mouth."""
        self._is_speaking = speaking

    def set_listening(self, listening: bool) -> None:
        """Indicate the robot is actively listening."""
        self._is_listening = listening

    def set_status(self, text: str) -> None:
        """Update the status text displayed below the face."""
        self._status_text = text

    def set_person_name(self, name: str) -> None:
        """Display the currently recognized person's name."""
        self._person_name = name

    def set_gaze(self, x: float, y: float) -> None:
        """Set normalized gaze direction [-1, 1] for each axis."""
        self._gaze_x = x
        self._gaze_y = y

    def start(self) -> None:
        """Start the avatar window in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name="AvatarThread",
            daemon=True,
        )
        self._thread.start()
        log.info("Avatar window started")

    def stop(self) -> None:
        """Stop the avatar window."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        log.info("Avatar window stopped")

    # ── Main Loop (runs in thread) ────────────────────────────────────────────

    def _run(self) -> None:
        try:
            import pygame
            from avatar.eyes import Eyes
            from avatar.mouth import Mouth
            from avatar.animations import PulseAnimator

            pygame.init()
            pygame.display.set_caption(self._title)
            screen = pygame.display.set_mode((self._width, self._height))
            clock = pygame.time.Clock()

            try:
                font_large  = pygame.font.SysFont("Arial", 28, bold=True)
                font_medium = pygame.font.SysFont("Arial", 20)
                font_small  = pygame.font.SysFont("Arial", 16)
            except Exception:
                font_large = font_medium = font_small = pygame.font.Font(None, 24)

            # Avatar components
            left_eye_center  = (self._width // 2 - 140, self._height // 2 - 60)
            right_eye_center = (self._width // 2 + 140, self._height // 2 - 60)
            eye_radius = 72

            eyes  = Eyes(screen, left_eye_center, right_eye_center, eye_radius)
            mouth = Mouth(screen, (self._width // 2, self._height // 2 + 100), 170)

            # Accent glow pulse
            glow_pulse = PulseAnimator(0.3, 0.8, 0.7)

            while self._running:
                # ── Event handling ────────────────────────────────────────────
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self._running = False

                # ── Background ────────────────────────────────────────────────
                screen.fill(BG_COLOR)

                # Face ellipse
                face_rect = pygame.Rect(
                    self._width // 2 - 220,
                    self._height // 2 - 200,
                    440, 380
                )
                pygame.draw.ellipse(screen, FACE_COLOR, face_rect)
                glow_alpha = int(glow_pulse.tick() * 80 + 20)
                outline_color = tuple(min(255, int(c * glow_pulse.tick() * 1.2))
                                      for c in FACE_OUTLINE)
                pygame.draw.ellipse(screen, outline_color, face_rect, 3)

                # ── Update emotion → expressions ──────────────────────────────
                emotion_val = self._emotion
                try:
                    eye_state   = _EMOTION_TO_EYE.get(emotion_val, EyeState.OPEN)
                    mouth_state = _EMOTION_TO_MOUTH.get(emotion_val, MouthState.NEUTRAL)
                except Exception:
                    eye_state   = EyeState.OPEN
                    mouth_state = MouthState.NEUTRAL

                if not self._is_speaking:
                    eyes.set_state(eye_state)
                    mouth.set_state(mouth_state)

                eyes.set_gaze(self._gaze_x, self._gaze_y)
                mouth.set_speaking(self._is_speaking)

                # ── Draw components ───────────────────────────────────────────
                eyes.draw()
                mouth.draw()

                # ── Status indicators ─────────────────────────────────────────
                self._draw_status_bar(screen, font_medium, font_small)

                # ── Person name ───────────────────────────────────────────────
                if self._person_name:
                    name_surf = font_large.render(
                        self._person_name, True, TEXT_COLOR
                    )
                    name_rect = name_surf.get_rect(
                        center=(self._width // 2, self._height - 55)
                    )
                    screen.blit(name_surf, name_rect)

                # ── State indicator dot ───────────────────────────────────────
                dot_color = (
                    SPEAKING_COLOR  if self._is_speaking  else
                    LISTENING_COLOR if self._is_listening else
                    (60, 80, 120)
                )
                pygame.draw.circle(screen, dot_color, (30, 30), 10)
                pygame.draw.circle(screen, FACE_OUTLINE, (30, 30), 10, 2)

                pygame.display.flip()
                clock.tick(self._fps)

        except ImportError:
            log.warning("pygame not available — avatar disabled")
        except Exception as exc:
            log.error(f"Avatar error: {exc}", exc_info=True)
        finally:
            try:
                import pygame as pg
                pg.quit()
            except Exception:
                pass

    def _draw_status_bar(
        self,
        screen: "pygame.Surface",
        font_medium: "pygame.font.Font",
        font_small: "pygame.font.Font",
    ) -> None:
        """Draw the status text bar at the bottom of the window."""
        import pygame

        # Bottom panel background
        panel = pygame.Rect(0, self._height - 40, self._width, 40)
        pygame.draw.rect(screen, PANEL_COLOR, panel)
        pygame.draw.line(screen, FACE_OUTLINE, (0, self._height - 40),
                         (self._width, self._height - 40), 1)

        # Status text
        state_str = (
            "🔊 Speaking..."  if self._is_speaking else
            "🎤 Listening..."  if self._is_listening else
            "💤 Idle"
        )

        txt = f"  {self._status_text}  |  {state_str}"
        surf = font_small.render(txt, True, TEXT_COLOR)
        screen.blit(surf, (10, self._height - 28))
