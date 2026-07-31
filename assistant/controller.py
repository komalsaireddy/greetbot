"""
GreetBot Main Assistant Controller
===================================
The central brain stem that coordinates all modules:
Vision, Tracking, Servos, Audio, STT, TTS, Avatar, Skills, and the LLM.
"""

import threading
import time
import re
from typing import Optional, List

from config import AVATAR_ENABLED, DEBUG, SERVO_ENABLED, CAMERA_ENABLED
from utils.logger import get_logger

# Vision
from vision.camera import Camera
from vision.face_detector import FaceDetector
from vision.face_tracking import FaceTracker
from vision.face_recognition import FaceRecognition
from vision.face_database import FaceDatabase

# Speech & Sensors
from speech.microphone import Microphone
from speech.stt import STT
from speech.tts import create_tts
from sensors.servo import ServoController

# Brain & Skills
from brain.llm import LLM
from memory.profile_manager import ProfileManager
from skills.system import is_system_query, get_system_info, format_system_info
from skills.weather import is_weather_query, extract_city, get_weather, format_weather
from skills.search import is_search_query, extract_search_query, search, format_search_result
from skills.wikipedia_skill import is_wikipedia_query, extract_wikipedia_query, search_wikipedia, format_wikipedia_result
from skills.vision import is_vision_query
from skills.telegram_bot import (
    is_file_send_query, extract_file_query, find_file,
    send_file, send_photo_frame, send_message
)

# Avatar
from avatar.face import AvatarFace


log = get_logger(__name__)


class AssistantController:
    """
    The orchestrator that runs the GreetBot main loops.

    Two main threads:
    1. Vision Loop (Main Thread): Captures frames, detects/tracks faces,
       controls servos, and updates the avatar display.
    2. Speech Loop (Background Thread): Listens for audio, runs STT,
       processes skills/LLM, and speaks TTS.
    """

    def __init__(self) -> None:
        log.info("Initializing GreetBot Controller...")

        # ── Vision & Tracking ─────────────────────────────────────────────────
        self.camera: Optional[Camera] = None
        if CAMERA_ENABLED:
            self.camera = Camera()
        self.face_detector = FaceDetector()
        self.face_tracker = FaceTracker()
        self.face_recognition = FaceRecognition()
        self.face_db = FaceDatabase()
        self.profiles = ProfileManager()

        # ── Hardware & Avatar ─────────────────────────────────────────────────
        self.servo: Optional[ServoController] = None
        if SERVO_ENABLED:
            self.servo = ServoController()
            
        self.avatar: Optional[AvatarFace] = None
        if AVATAR_ENABLED:
            self.avatar = AvatarFace()

        # ── Speech ────────────────────────────────────────────────────────────
        self.microphone = Microphone()
        self.stt = STT()
        self.tts = create_tts()

        # ── Brain ─────────────────────────────────────────────────────────────
        self.brain = LLM()

        # State
        self.running: bool = False
        self.is_speaking: bool = False
        self.is_listening: bool = False
        self._speech_thread: Optional[threading.Thread] = None
        self._tts_lock = threading.Lock()
        self._face_recognition_lock = threading.Lock()
        self._pending_unknown: Optional[tuple[object, dict]] = None
        self._telegram_alert_sent_for: Optional[str] = None  # track_id of last alerted face

        # Current primary person (the closest or most central face)
        self.current_person_name: str = ""
        self.current_person_id: str = ""
        self.current_person_visit_count: int = 0
        self.person_visible_time: float = 0.0

        # Memory of who we greeted recently to avoid spam
        self.recently_greeted: dict[str, float] = {}
        self.GREET_COOLDOWN = 60.0  # seconds

    # ── Startup & Shutdown ────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the assistant background threads and begin the main loop."""
        self.running = True

        self.microphone.start()

        # Start background speech loop
        self._speech_thread = threading.Thread(
            target=self._speech_loop,
            name="SpeechLoopThread",
            daemon=True,
        )
        self._speech_thread.start()

        # Speak startup greeting
        self._speak("Systems online. I am ready.")

        if self.avatar:
            self.avatar.set_status("Ready")
            # Run vision loop in a background thread
            self._vision_thread = threading.Thread(
                target=self._vision_loop,
                name="VisionLoopThread",
                daemon=True,
            )
            self._vision_thread.start()
            
            try:
                # Avatar MUST run on main thread for macOS PyGame compatibility
                self.avatar.run_on_main_thread()
            except KeyboardInterrupt:
                log.info("Keyboard interrupt received")
            except Exception as exc:
                log.error(f"Fatal error in avatar loop: {exc}", exc_info=True)
            finally:
                self.stop()
        else:
            # If no avatar, run vision loop on main thread
            try:
                self._vision_loop()
            except KeyboardInterrupt:
                log.info("Keyboard interrupt received")
            except Exception as exc:
                log.error(f"Fatal error in vision loop: {exc}", exc_info=True)
            finally:
                self.stop()

    def stop(self) -> None:
        """Gracefully shut down all components."""
        log.info("Shutting down GreetBot...")
        self.running = False

        self.microphone.stop()
        self.tts.stop()
        if self.servo:
            self.servo.stop()
        self.camera.release()

        if self.avatar:
            self.avatar.stop()

        if self._speech_thread and self._speech_thread.is_alive():
            self._speech_thread.join(timeout=3)
            
        log.info("Shutdown complete.")

    # ── Background Speech Loop ────────────────────────────────────────────────

    def _speech_loop(self) -> None:
        """
        Listens for audio, processes it, and generates TTS responses.
        Runs continuously in a background thread.
        """
        while self.running:
            # Block until wake word is detected
            if not self.microphone.wait_for_wakeword():
                time.sleep(0.1)
                continue

            if self.is_speaking:
                log.info("Interrupted! Stopping speech.")
                self.tts.stop()
                self.is_speaking = False

            try:
                self.is_listening = True
                if self.avatar:
                    self.avatar.set_listening(True)

                # Block until audio is captured
                audio_file = self.microphone.listen("input.wav")

                self.is_listening = False
                if self.avatar:
                    self.avatar.set_listening(False)

                if audio_file is None:
                    continue

                text = self.stt.transcribe(audio_file)
                if not text:
                    continue

                log.info(f"User said: {text}")

                if self._check_exit_commands(text):
                    self.running = False
                    break

                self._handle_user_input(text)

            except Exception as exc:
                log.error(f"Speech loop error: {exc}", exc_info=True)
                self.is_listening = False
                if self.avatar:
                    self.avatar.set_listening(False)

    def _check_exit_commands(self, text: str) -> bool:
        """Return True if the user asked to shut down."""
        exit_phrases = ["shut down", "go to sleep", "turn off", "exit", "quit"]
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in exit_phrases):
            self._speak("Shutting down. Goodbye.")
            return True
        return False

    def _handle_user_input(self, text: str) -> None:
        """Route user text to skills or the LLM brain."""
        registered_name = self._register_pending_person(text)
        if registered_name:
            self._speak(f"Nice to meet you, {registered_name}. I will remember you.")
            return

        # 1. System Info Skill
        if is_system_query(text):
            info = get_system_info()
            self._speak(format_system_info(info))
            return

        # 2. Weather Skill
        if is_weather_query(text):
            city = extract_city(text)
            self._speak(format_weather(get_weather(city)))
            return

        # 2.5. Vision Skill
        if is_vision_query(text):
            if not self.camera:
                self._speak("I can't see right now because my camera is disabled.")
                return
            b64_img = self._get_base64_frame()
            if b64_img:
                self._speak(self.brain.describe_vision(b64_img, text))
            else:
                self._speak("I'm having trouble seeing right now.")
            return

        # 3. Web Search Skill
        if is_search_query(text):
            query = extract_search_query(text)
            search_res = search(query)
            if search_res:
                self._speak(format_search_result(query, search_res))
                return
            else:
                log.info(f"Web search for {query!r} failed, falling back to Wikipedia/LLM.")

        # 3.5. Wikipedia Skill
        if is_wikipedia_query(text):
            query = extract_wikipedia_query(text)
            wiki_res = search_wikipedia(query)
            if wiki_res:
                self._speak(format_wikipedia_result(query, wiki_res))
                return
            else:
                log.info(f"Wikipedia search for {query!r} failed, falling back to LLM.")

        # 3.7. Telegram File Send Skill
        if is_file_send_query(text):
            file_query = extract_file_query(text)
            self._speak(f"Let me look for that file. One moment.")
            found = find_file(file_query)
            if found:
                import threading
                threading.Thread(
                    target=lambda: send_file(found),
                    daemon=True
                ).start()
                import os
                self._speak(f"Found it! Sending {os.path.basename(found)} to Telegram now.")
            else:
                self._speak(f"I couldn't find a file matching '{file_query}'. Try saying the exact filename.")
            return

        # 4. Fallback to Brain (LLM)
        reply = self.brain.ask(
            user_text=text,
            person_name=self.current_person_name or None,
            person_id=self.current_person_id or None,
            person_count=self.face_tracker.track_count,
        )
        self._speak(reply)

    def _register_pending_person(self, text: str) -> Optional[str]:
        """Enroll the currently visible stranger after an explicit name phrase."""
        if not self._pending_unknown:
            return None

        match = re.match(
            r"^\s*(?:my name is|call me)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s*[.!?]*\s*$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        from utils.helpers import normalize_name

        name = normalize_name(match.group(1))
        if not name:
            return None

        frame, face = self._pending_unknown
        try:
            self.face_db.register_person(name, frame, face, n_captures=1)
            with self._face_recognition_lock:
                self.face_recognition.reload()
            profile = self.profiles.get_or_create(name)
            self.current_person_name = name
            self.current_person_id = profile["id"]
            self.current_person_visit_count = int(profile["visit_count"])
            self._pending_unknown = None
            log.info("Registered person by voice: %s", name)
            return name
        except Exception as exc:
            log.error("Person registration failed: %s", exc, exc_info=True)
            return None

    def _get_base64_frame(self) -> Optional[str]:
        if not self.camera:
            return None
        import cv2
        import base64
        frame = self.camera.get_frame()
        if frame is None:
            return None
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return None
        return base64.b64encode(buffer).decode('utf-8')

    def _speak(self, text: str) -> None:
        """Synthesize and play speech, updating avatar states."""
        if not text:
            return

        # One audio device can play only one response at a time.  The lock
        # prevents a greeting and a conversational answer from overlapping.
        with self._tts_lock:
            self.is_speaking = True
            if self.avatar:
                self.avatar.set_speaking(True)
                self.avatar.set_emotion(self.brain.current_emotion)

            try:
                self.tts.speak(text)
            except Exception as exc:
                log.error(f"TTS error: {exc}")
            finally:
                self.is_speaking = False
                if self.avatar:
                    self.avatar.set_speaking(False)

    # ── Main Vision Loop ──────────────────────────────────────────────────────

    def _vision_loop(self) -> None:
        """
        Captures frames, runs face detection/recognition, controls servos,
        and manages presence detection.
        Runs in the main thread (required by some GUI/camera libs).
        """
        import cv2

        while self.running:
            if not self.camera:
                time.sleep(1.0)
                continue

            frame = self.camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_h, frame_w = frame.shape[:2]

            # 1. Fast Pre-Detection (Haar)
            # Skip expensive face_recognition if no faces exist
            if not self.face_detector.has_face(frame):
                self._handle_no_faces()
                if DEBUG:
                    cv2.imshow("GreetBot Debug", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.running = False
                continue

            # 2. Heavy Face Recognition (every N frames)
            if self.camera.should_run_recognition():
                with self._face_recognition_lock:
                    raw_faces = self.face_recognition.recognize(frame)
                tracks = self.face_tracker.update(raw_faces)
            else:
                tracks = self.face_tracker.update([])

            # 3. Find primary face to track
            if tracks:
                # Track the largest face or the closest one to center
                primary = max(tracks, key=lambda t: (t.right - t.left) * (t.bottom - t.top))
                
                # Servo tracking
                if self.servo:
                    self.servo.track_face(primary.center_x, primary.center_y, frame_w, frame_h)

                # Avatar gaze tracking
                if self.avatar:
                    self.avatar.set_gaze_toward(primary.center_x, primary.center_y, frame_w, frame_h)
                    self.avatar.set_person_name(
                        primary.name if _is_known_name(primary.name) else "Stranger"
                    )

                if not _is_known_name(primary.name):
                    self._pending_unknown = (
                        frame.copy(),
                        {
                            "left": primary.left,
                            "top": primary.top,
                            "right": primary.right,
                            "bottom": primary.bottom,
                        },
                    )
                    # Send Telegram alert for unknown visitor (throttled)
                    alert_frame = frame.copy()
                    threading.Thread(
                        target=lambda f=alert_frame: send_photo_frame(
                            f, caption="🚨 Unknown visitor detected at GreetBot!"
                        ),
                        daemon=True,
                    ).start()

                self._handle_presence(primary.name, primary.track_id)
            else:
                self._handle_no_faces()

            # 4. Debug output
            if DEBUG:
                for t in tracks:
                    cv2.rectangle(frame, (t.left, t.top), (t.right, t.bottom), (0, 255, 0), 2)
                    label = f"{t.name} ({int(t.confidence)}%)" if t.name != "Unknown" else "Unknown"
                    cv2.putText(frame, label, (t.left, t.top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                cv2.imshow("GreetBot Debug", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    break

    def _handle_presence(self, name: str, track_id: int) -> None:
        """Handle greetings and identity for the primary tracked person."""
        # Update current person state
        if self.current_person_name != name:
            self.current_person_name = name
            if _is_known_name(name):
                existing = self.profiles.load_by_name(name)
                profile = self.profiles.get_or_create(name)
                if existing:
                    self.profiles.update_last_seen(profile["id"])
                    profile = self.profiles.load(profile["id"]) or profile
                self.current_person_id = profile["id"]
                self.current_person_visit_count = int(profile["visit_count"])
            else:
                self.current_person_id = f"unknown_{track_id}"
                self.current_person_visit_count = 0
            self.person_visible_time = time.time()

        # Proactive Greeting logic
        now = time.time()
        visible_duration = now - self.person_visible_time

        # If they've been visible for > 1 second and we aren't speaking
        if visible_duration > 1.0 and not self.is_speaking and not self.is_listening:
            last_greeted = self.recently_greeted.get(self.current_person_id, 0.0)
            
            # If cooldown expired, greet them
            if (now - last_greeted) > self.GREET_COOLDOWN:
                self.recently_greeted[self.current_person_id] = now
                
                # LLM/network work must not freeze the camera and servo loop.
                threading.Thread(
                    target=self._generate_and_speak_greeting,
                    args=(name, self.current_person_id, self.current_person_visit_count),
                    daemon=True,
                    name="GreetingThread",
                ).start()

    def _generate_and_speak_greeting(
        self, name: str, person_id: str, visit_count: int
    ) -> None:
        """Generate a greeting away from the camera loop, then play it."""
        if not _is_known_name(name):
            greeting = self.brain.generate_registration_message()
        else:
            greeting = self.brain.generate_greeting(name, person_id, visit_count)
        # Do not greet a person who has already left or been replaced.
        if self.running and self.current_person_id == person_id:
            self._speak(greeting)

    def _handle_no_faces(self) -> None:
        """Behavior when no faces are detected."""
        if self.servo:
            self.servo.center()
        
        if self.avatar:
            self.avatar.set_gaze(0, 0)
            self.avatar.set_person_name("")
            self.avatar.set_emotion("NEUTRAL")

        # Clear current person if nobody is visible
        if self.current_person_id:
            # Tell LLM session to close for that person
            self.brain.end_person_session(self.current_person_id)
            self.current_person_name = ""
            self.current_person_id = ""
            self.current_person_visit_count = 0
            self.person_visible_time = 0.0
        self._pending_unknown = None


def _is_known_name(name: str) -> bool:
    """Return whether a recognition label represents an enrolled person."""
    return bool(name and name != "Unknown" and not name.startswith("person_"))
