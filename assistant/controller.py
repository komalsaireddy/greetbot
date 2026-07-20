import threading
import time
import cv2

from brain.llm import LLM
from speech.microphone import Microphone
from speech.stt import STT
from speech.tts import TTS

from vision.camera import Camera
from vision.face_recognition import FaceRecognition
from vision.perception import Perception
from vision.face_database import FaceDatabase


class AssistantController:

    def __init__(self):

        print("\n========== GreetBot ==========")
        print("Initializing Modules...\n")

        self.brain = LLM()
        self.microphone = Microphone()
        self.stt = STT()
        self.tts = TTS()

        self.camera = Camera()
        self.face_ai = FaceRecognition()
        self.perception = Perception()

        self.face_db = FaceDatabase()

        self.running = True
        self.greeted = set()
        self.speaking = False

        # Prevent saving the same unknown face repeatedly
        self.saved_unknowns = set()

        self.microphone.start()

    def greet_new_people(self):

        for person in self.perception.get_known_people():

            name = person["name"]

            if name in self.greeted:
                continue

            self.greeted.add(name)

            self.speaking = True
            self.tts.speak(f"Hello {name}. Welcome back.")
            self.speaking = False

    def speech_loop(self):

        while self.running:

            if self.speaking:
                time.sleep(0.1)
                continue

            try:

                audio = self.microphone.listen()

                text = self.stt.transcribe(audio)

                if not text:
                    continue

                print(f"\n🗣 You: {text}")

                if text.lower() in (
                    "quit",
                    "exit",
                    "bye",
                    "goodbye",
                    "stop",
                ):
                    self.running = False
                    break

                self.speaking = True

                reply = self.brain.ask(text)

                print(f"\n🤖 GreetBot: {reply}")

                self.tts.speak(reply)

                self.speaking = False

            except Exception as e:

                print(e)

                self.speaking = False

    def run(self):

        self.speaking = True
        self.tts.speak("Hello. I am GreetBot.")
        self.speaking = False

        threading.Thread(
            target=self.speech_loop,
            daemon=True,
        ).start()

        while self.running:

            frame = self.camera.get_frame()

            if frame is None:
                continue

            faces = self.face_ai.recognize(frame)

            # Save unknown faces
            for face in faces:

                if face["name"] == "Unknown":

                    key = (
                        face["left"] // 40,
                        face["top"] // 40
                    )

                    if key not in self.saved_unknowns:

                        self.face_db.save_unknown_face(frame, face)

                        self.saved_unknowns.add(key)

            self.perception.update(faces)

            self.greet_new_people()

            for face in faces:

                cv2.rectangle(
                    frame,
                    (face["left"], face["top"]),
                    (face["right"], face["bottom"]),
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    face["name"],
                    (face["left"], face["top"] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

            cv2.imshow("GreetBot", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.running = False
                break

        self.microphone.stop()
        self.camera.release()
        cv2.destroyAllWindows()
