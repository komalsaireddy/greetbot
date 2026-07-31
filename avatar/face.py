"""
GreetBot Avatar Face
=====================
Main avatar compositor — assembles EVE/Wall-E LED visor eyes + mouth
and manages a pygame window running in a background thread.
"""

import threading
import time
import random
import numpy as np
from typing import Optional

from utils.logger import get_logger
from brain.emotion import Emotion

log = get_logger(__name__)


# ── Colors ────────────────────────────────────────────────────────────────────
BG_COLOR          = (10,  12,  20)   # Visor screen base
PANEL_COLOR       = (16,  20,  35)   # Bottom UI dashboard
TEXT_COLOR        = (170, 180, 210)
STATUS_COLOR      = (0, 255, 150)
LISTENING_COLOR   = (255, 180,  50)
SPEAKING_COLOR    = (80,  160, 255)


class AvatarFace:
    def __init__(
        self,
        width: int = 800,
        height: int = 480,
        fps: int = 30,
        title: str = "GreetBot Control Core",
    ) -> None:
        self._width = width
        self._height = height
        self._fps = fps
        self._title = title

        # Shared state
        self._emotion: str = Emotion.NEUTRAL
        self._is_speaking: bool = False
        self._is_listening: bool = False
        self._status_text: str = "Initializing..."
        self._person_name: str = ""
        self._running: bool = False
        self._is_fullscreen: bool = False

        self._gaze_x: float = 0.0
        self._gaze_y: float = 0.0

        self._thread: Optional[threading.Thread] = None

        # Graphics engine states
        self._blink_state = {"next_blink_at": 0, "blinking_until": 0}
        self._emotion_transition = {"current": "NEUTRAL", "previous": "NEUTRAL", "start": 0, "duration": 250}

    # ── Public API ────────────────────────────────────────────────────────────

    def set_emotion(self, emotion: str) -> None:
        self._emotion = emotion

    def set_speaking(self, speaking: bool) -> None:
        self._is_speaking = speaking

    def set_listening(self, listening: bool) -> None:
        self._is_listening = listening

    def set_status(self, text: str) -> None:
        self._status_text = text

    def set_person_name(self, name: str) -> None:
        self._person_name = name

    def set_gaze(self, x: float, y: float) -> None:
        self._gaze_x = x
        self._gaze_y = y

    def set_gaze_toward(self, face_cx: int, face_cy: int, frame_w: int, frame_h: int) -> None:
        # Normalize to [-1, 1] (invert X because camera mirror)
        nx = -(face_cx / frame_w - 0.5) * 2.0
        ny = (face_cy / frame_h - 0.5) * 2.0
        self.set_gaze(nx, ny)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name="AvatarThread",
            daemon=True,
        )
        self._thread.start()
        log.info("Avatar window started")

    def run_on_main_thread(self) -> None:
        self._running = True
        log.info("Avatar window started on main thread")
        self._run()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        log.info("Avatar window stopped")

    # ── Graphics Engine ────────────────────────────────────────────

    def _update_blink_clock(self):
        import pygame
        now = pygame.time.get_ticks()
        if now > self._blink_state["next_blink_at"] and now > self._blink_state["blinking_until"]:
            self._blink_state["blinking_until"] = now + 120
            self._blink_state["next_blink_at"] = now + random.randint(2500, 6000)

    def _is_blinking(self):
        import pygame
        return pygame.time.get_ticks() < self._blink_state["blinking_until"]

    def _update_emotion_transition(self):
        import pygame
        now = pygame.time.get_ticks()
        target = self._emotion
        if target != self._emotion_transition["current"]:
            self._emotion_transition["previous"] = self._emotion_transition["current"]
            self._emotion_transition["current"] = target
            self._emotion_transition["start"] = now

    def _get_transition_progress(self):
        import pygame
        elapsed = pygame.time.get_ticks() - self._emotion_transition["start"]
        return min(1.0, elapsed / self._emotion_transition["duration"])

    def _get_blended_eye_surface(self, side):
        import pygame
        progress = self._get_transition_progress()
        to_emotion = self._emotion_transition["current"]
        from_emotion = self._emotion_transition["previous"]

        if progress >= 1.0 or from_emotion == to_emotion:
            return self._get_high_res_eye_surface(to_emotion, side)

        from_surf = self._get_high_res_eye_surface(from_emotion, side)
        to_surf = self._get_high_res_eye_surface(to_emotion, side)

        blended = pygame.Surface((160, 140), pygame.SRCALPHA)
        from_surf.set_alpha(int((1.0 - progress) * 255))
        to_surf.set_alpha(int(progress * 255))
        blended.blit(from_surf, (0, 0))
        blended.blit(to_surf, (0, 0))
        return blended

    def _get_high_res_eye_surface(self, emotion, side):
        import pygame
        surf = pygame.Surface((160, 140), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        eye_color = (0, 210, 255)
        white_color = (255, 255, 255)
        cx, cy = 80, 70

        base_w, base_h = 90, 100
        openness = 1.0
        brow_y_offset = 0
        brow_tilt = 0

        if emotion == "HAPPY":
            points = []
            for angle in range(210, 331, 5):
                rad = np.radians(angle)
                px = cx + 55 * np.cos(rad)
                py = cy + 15 + 35 * np.sin(rad)
                points.append((px, py))
            pygame.draw.lines(surf, eye_color, False, points, 14)

            lash_x = cx + side * 45
            lash_y = cy - 5
            pygame.draw.line(surf, eye_color, (lash_x, lash_y), (lash_x + side * 15, lash_y - 10), 8)

            brow_y = cy - 45
            pygame.draw.arc(surf, eye_color, (cx - 45, brow_y, 90, 30), 0.5, 2.6, 6)
            return surf
        elif emotion == "SAD":
            openness = 0.52
            brow_y_offset = 12
            brow_tilt = side * 15
        elif emotion == "SURPRISED":
            base_w, base_h = 108, 108
            openness = 1.1
            brow_y_offset = -14
        elif emotion == "THINKING":
            if side < 0:
                openness = 0.85
                brow_y_offset = -5
                brow_tilt = -8
            else:
                openness = 0.32
                brow_y_offset = 10
                brow_tilt = 12

        if self._is_blinking():
            openness = 0.02

        lid_pts = []
        for angle in range(190, 351, 5):
            rad = np.radians(angle)
            px = cx + (base_w // 2 + 5) * np.cos(rad)
            py = cy - (base_h // 2) * openness * 0.2 + (base_h // 2) * openness * np.sin(rad)
            lid_pts.append((px, py))

        tilt_deg = 0
        if emotion == "NEUTRAL":
            tilt_deg = -8 * side
        elif emotion == "SAD":
            tilt_deg = 15 * side
        elif emotion == "THINKING":
            tilt_deg = -10 if side < 0 else 12

        def rotate_point(pt, angle_deg, center):
            angle_rad = np.radians(angle_deg)
            ox, oy = center
            px, py = pt
            qx = ox + np.cos(angle_rad) * (px - ox) - np.sin(angle_rad) * (py - oy)
            qy = oy + np.sin(angle_rad) * (px - ox) + np.cos(angle_rad) * (py - oy)
            return int(qx), int(qy)

        rotated_lid = [rotate_point(p, tilt_deg, (cx, cy)) for p in lid_pts]
        pygame.draw.lines(surf, eye_color, False, rotated_lid, 10)

        outer_idx = -1 if side > 0 else 0
        outer_pt = rotated_lid[outer_idx]
        pygame.draw.line(surf, eye_color, outer_pt, (outer_pt[0] + side * 16, outer_pt[1] - 8), 8)

        eye_h = int(base_h * openness)
        if eye_h > 15:
            iris_w = int(base_w * 0.72)
            iris_h = int(eye_h * 0.85)
            iris_surf = pygame.Surface((iris_w, iris_h), pygame.SRCALPHA)
            iris_surf.fill((0, 0, 0, 0))
            pygame.draw.ellipse(iris_surf, eye_color, (0, 0, iris_w, iris_h))
            hl1_cx = int(iris_w * 0.35)
            hl1_cy = int(iris_h * 0.3)
            hl1_r = int(min(iris_w, iris_h) * 0.18)
            pygame.draw.circle(iris_surf, white_color, (hl1_cx, hl1_cy), hl1_r)
            hl2_cx = int(iris_w * 0.7)
            hl2_cy = int(iris_h * 0.7)
            hl2_r = int(min(iris_w, iris_h) * 0.09)
            pygame.draw.circle(iris_surf, white_color, (hl2_cx, hl2_cy), hl2_r)

            rotated_iris = pygame.transform.rotate(iris_surf, -tilt_deg)
            r_rect = rotated_iris.get_rect()
            
            # Gaze adjustment
            gaze_off_x = int(self._gaze_x * 15)
            gaze_off_y = int(self._gaze_y * 15)
            
            r_rect.center = (cx + gaze_off_x, cy + gaze_off_y)
            surf.blit(rotated_iris, r_rect)

        pygame.draw.lines(surf, eye_color, False, rotated_lid, 8)
        brow_y = cy - base_h * 0.6 + brow_y_offset
        brow_half = base_w * 0.5
        brow_p1 = (cx - brow_half, brow_y + brow_tilt)
        brow_p2 = (cx + brow_half, brow_y - brow_tilt)
        rot_p1 = rotate_point(brow_p1, tilt_deg * 0.5, (cx, cy))
        rot_p2 = rotate_point(brow_p2, tilt_deg * 0.5, (cx, cy))
        pygame.draw.line(surf, eye_color, rot_p1, rot_p2, 6)

        return surf

    def _draw_led_grid(self, dest_screen, src_surf, cx, cy, grid_spacing=4):
        import pygame
        w, h = src_surf.get_size()
        grid_w = w // grid_spacing
        grid_h = h // grid_spacing

        low_res = pygame.transform.scale(src_surf, (grid_w, grid_h))
        start_x = cx - (grid_w * grid_spacing) // 2
        start_y = cy - (grid_h * grid_spacing) // 2

        for y in range(grid_h):
            for x in range(grid_w):
                color = low_res.get_at((x, y))
                if color.a > 0 and (color.r > 10 or color.g > 10 or color.b > 10):
                    px = start_x + x * grid_spacing + grid_spacing // 2
                    py = start_y + y * grid_spacing + grid_spacing // 2

                    is_highlight = (color.r > 220 and color.g > 220 and color.b > 220)
                    if is_highlight:
                        core_color = (255, 255, 255)
                        glow_color = (0, 100, 220)
                    else:
                        core_color = (130, 240, 255)
                        glow_color = (0, 80, 180)

                    pygame.draw.circle(dest_screen, glow_color, (px, py), grid_spacing * 0.75)
                    pygame.draw.circle(dest_screen, core_color, (px, py), grid_spacing * 0.38)

    def _draw_glowing_mouth(self, screen, cx, cy, emotion, talking=False):
        import pygame
        color = (130, 240, 255)
        glow_color = (0, 80, 180)

        if talking:
            wobble = abs(np.sin(pygame.time.get_ticks() / 90.0))
            mouth_h = int(6 + wobble * 22)
            rect = pygame.Rect(cx - 26, cy - mouth_h // 2, 52, mouth_h)
            pygame.draw.ellipse(screen, glow_color, rect, 8)
            pygame.draw.ellipse(screen, color, rect, 4)
            return
        
        if emotion == "HAPPY":
            rect = pygame.Rect(cx - 30, cy - 10, 60, 30)
            pygame.draw.arc(screen, glow_color, rect, 3.5, 5.9, 8)
            pygame.draw.arc(screen, color, rect, 3.5, 5.9, 4)
        elif emotion == "SAD":
            rect = pygame.Rect(cx - 24, cy, 48, 24)
            pygame.draw.arc(screen, glow_color, rect, 0.4, 2.7, 8)
            pygame.draw.arc(screen, color, rect, 0.4, 2.7, 4)
        elif emotion == "SURPRISED":
            pygame.draw.ellipse(screen, glow_color, pygame.Rect(cx - 12, cy - 8, 24, 20), 8)
            pygame.draw.ellipse(screen, color, pygame.Rect(cx - 12, cy - 8, 24, 20), 4)
        elif emotion == "THINKING":
            pygame.draw.line(screen, glow_color, (cx - 15, cy + 3), (cx + 15, cy - 3), 8)
            pygame.draw.line(screen, color, (cx - 15, cy + 3), (cx + 15, cy - 3), 4)
        else:
            pygame.draw.line(screen, glow_color, (cx - 18, cy), (cx + 18, cy), 8)
            pygame.draw.line(screen, color, (cx - 18, cy), (cx + 18, cy), 4)

    def _draw_visor_scanlines(self, screen, width, visor_h):
        import pygame
        for y in range(0, visor_h, 4):
            pygame.draw.line(screen, (12, 16, 32), (0, y), (width, y), 1)

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            import pygame

            pygame.init()
            pygame.display.set_caption(self._title)
            screen = pygame.display.set_mode((self._width, self._height))
            clock = pygame.time.Clock()

            try:
                font_medium = pygame.font.SysFont("Courier", 16, bold=True)
            except Exception:
                font_medium = pygame.font.Font(None, 24)

            visor_h = self._height - 110

            while self._running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self._running = False
                        elif event.key == pygame.K_f:
                            self._is_fullscreen = not self._is_fullscreen
                            if self._is_fullscreen:
                                screen = pygame.display.set_mode((self._width, self._height), pygame.FULLSCREEN)
                            else:
                                screen = pygame.display.set_mode((self._width, self._height))

                # Visor background
                screen.fill(BG_COLOR)
                self._draw_visor_scanlines(screen, self._width, visor_h)

                self._update_blink_clock()
                self._update_emotion_transition()
                
                emotion = self._emotion_transition["current"]

                left_eye_center = (self._width // 2 - 150, visor_h // 2)
                right_eye_center = (self._width // 2 + 150, visor_h // 2)
                mouth_center = (self._width // 2, visor_h // 2 + 95)

                left_eye_surf = self._get_blended_eye_surface(side=-1)
                right_eye_surf = self._get_blended_eye_surface(side=1)

                self._draw_led_grid(screen, left_eye_surf, left_eye_center[0], left_eye_center[1], grid_spacing=4)
                self._draw_led_grid(screen, right_eye_surf, right_eye_center[0], right_eye_center[1], grid_spacing=4)

                self._draw_glowing_mouth(screen, mouth_center[0], mouth_center[1], emotion, talking=self._is_speaking)

                # Bottom UI Dashboard
                dash_rect = pygame.Rect(0, visor_h, self._width, self._height - visor_h)
                pygame.draw.rect(screen, PANEL_COLOR, dash_rect)
                pygame.draw.line(screen, (35, 42, 68), (0, visor_h), (self._width, visor_h), 2)
                    
                state_str = (
                    "🔊 SPEAKING..."  if self._is_speaking else
                    "🎤 LISTENING..."  if self._is_listening else
                    "💤 IDLE"
                )

                person_str = f" | TRACKING: {self._person_name}" if self._person_name else ""
                
                label_status = font_medium.render(f"SYSTEM STATUS : {self._status_text} | {state_str}{person_str}", True, STATUS_COLOR)
                screen.blit(label_status, (20, visor_h + 12))

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
