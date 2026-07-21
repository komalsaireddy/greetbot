"""
GreetBot Main Assistant Controller
===================================
The central brain stem that coordinates all modules:
Vision, Tracking, Servos, Audio, STT, TTS, Avatar, Skills, and the LLM.
"""

import threading
import time
from typing import Optional, List

from config import AVATAR_ENABLED, DEBUG, SERVO_ENABLED
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
from skills.system import is_system_query, get_system_info, format_system_info
from skills.weather import is_weather_query, extract_city, get_weather, format_weather
from skills.search import is_search_query, extract_search_query, search, format_search_result

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
        self.camera = Camera()
        self.face_detector = FaceDetector()
        self.face_tracker = FaceTracker()
        self.face_recognition = FaceRecognition()
        self.face_db = FaceDatabase()

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

        # Current primary person (the closest or most central face)
        self.current_person_name: str = ""
        self.current_person_id: str = ""
        self.person_visible_time: float = 0.0

        # Memory of who we greeted recently to avoid spam
        self.recently_greeted: dict[str, float] = {}
        self.GREET_COOLDOWN = 60.0  # seconds

    # ── Startup & Shutdown ────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the assistant background threads and begin the main loop."""
        self.running = True

        if self.avatar:
            self.avatar.start()
            self.avatar.set_status("Initializing...")

        self.microphone.start()

        # Start background speech loop
        threading.Thread(
            target=self._speech_loop,
            name="SpeechLoopThread",
            daemon=True,
        ).start()

        # Speak startup greeting
        self._speak("Systems online. I am ready.")

        if self.avatar:
            self.avatar.set_status("Ready")

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
        if self.servo:
            self.servo.stop()
        self.camera.release()
        
        if self.avatar:
            self.avatar.stop()
            
        log.info("Shutdown complete.")

    # ── Background Speech Loop ────────────────────────────────────────────────

    def _speech_loop(self) -> None:
        """
        Listens for audio, processes it, and generates TTS responses.
        Runs continuously in a background thread.
        """
        while self.running:
            if self.is_speaking:
                time.sleep(0.1)
                continue

            try:
                self.is_listening = True
                if self.avatar:
                    self.avatar.set_listening(True)

                # Block until audio is captured
                audio_file = self.microphone.listen()

                self.is_listening = False
                if self.avatar:
                    self.avatar.set_listening(False)

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

        # 3. Web Search Skill
        if is_search_query(text):
            query = extract_search_query(text)
            self._speak(format_search_result(query, search(query)))
            return

        # 4. Fallback to Brain (LLM)
        reply = self.brain.ask(
            user_text=text,
            person_name=self.current_person_name or None,
            person_id=self.current_person_id or None,
            person_count=self.face_tracker.track_count,
        )
        self._speak(reply)

    def _speak(self, text: str) -> None:
        """Synthesize and play speech, updating avatar states."""
        if not text:
            return

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
                    self.avatar.set_person_name(primary.name if primary.name != "Unknown" else "Stranger")

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
            self.current_person_id = name.lower().replace(" ", "_") if name != "Unknown" else f"unknown_{track_id}"
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
                
                # Use LLM to generate a contextual greeting based on memory
                if name != "Unknown":
                    # For known persons, generate a personalized greeting
                    # In a real app, we'd look up visit count from profile
                    greeting = self.brain.generate_greeting(name, self.current_person_id, visit_count=5)
                else:
                    # For unknown persons, ask for their name
                    greeting = self.brain.generate_registration_message()

                # Dispatch speak in background to not block vision loop
                threading.Thread(target=self._speak, args=(greeting,), daemon=True).start()

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
            self.person_visible_time = 0.0
