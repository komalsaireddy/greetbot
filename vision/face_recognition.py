import os
import re
import cv2
import numpy as np
import face_recognition

from config import FACE_RECOGNITION_SCALE, FACE_RECOGNITION_THRESHOLD, VISION_FACES_DIR
from utils.logger import get_logger

log = get_logger(__name__)


class FaceRecognition:

    def __init__(self, faces_dir: str = str(VISION_FACES_DIR)):

        self.faces_dir = faces_dir

        self.known_encodings = []
        self.known_names = []

        os.makedirs(self.faces_dir, exist_ok=True)

        self.load_faces()

    def load_faces(self):

        self.known_encodings.clear()
        self.known_names.clear()

        log.info("Loading known faces...")

        for item in sorted(os.listdir(self.faces_dir)):

            path = os.path.join(self.faces_dir, item)

            # Support folders containing multiple images
            if os.path.isdir(path):

                person_name = item

                for file in os.listdir(path):

                    if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                        continue

                    image_path = os.path.join(path, file)

                    image = face_recognition.load_image_file(image_path)

                    encodings = face_recognition.face_encodings(image)

                    if len(encodings) == 0:
                        continue

                    self.known_encodings.append(encodings[0])
                    self.known_names.append(person_name)

                log.info("Loaded face samples for: %s", person_name)

            else:

                if not item.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                image = face_recognition.load_image_file(path)

                encodings = face_recognition.face_encodings(image)

                if len(encodings) == 0:
                    log.warning("Skipped %s (no face detected)", item)
                    continue

                self.known_encodings.append(encodings[0])

                name = os.path.splitext(item)[0]
                # Legacy flat samples such as Komal.jpg and Komal2.jpg are
                # samples of the same person.  New registrations use folders.
                if not name.startswith("person_"):
                    name = re.sub(r"_?\\d+$", "", name)

                self.known_names.append(name)

                log.info("Loaded: %s", name)

        log.info("Total face encodings loaded: %d", len(self.known_encodings))

    def reload(self):

        self.load_faces()

    def recognize(self, frame):

        scale = FACE_RECOGNITION_SCALE
        if not 0 < scale <= 1:
            log.warning("Invalid FACE_RECOGNITION_SCALE=%s; using full frame", scale)
            scale = 1.0

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if scale != 1.0:
            rgb = cv2.resize(rgb, (0, 0), fx=scale, fy=scale)

        locations = face_recognition.face_locations(
            rgb,
            model="hog"
        )

        encodings = face_recognition.face_encodings(
            rgb,
            locations
        )

        faces = []

        for encoding, location in zip(encodings, locations):

            name = "Unknown"
            confidence = 0.0

            if len(self.known_encodings):

                distances = face_recognition.face_distance(
                    self.known_encodings,
                    encoding
                )

                best = np.argmin(distances)

                if distances[best] < FACE_RECOGNITION_THRESHOLD:

                    name = self.known_names[best]

                    confidence = (1 - distances[best]) * 100

            top, right, bottom, left = location
            if scale != 1.0:
                top = round(top / scale)
                right = round(right / scale)
                bottom = round(bottom / scale)
                left = round(left / scale)

            faces.append({

                "name": name,

                "confidence": round(confidence, 1),

                "encoding": encoding,

                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom

            })

        return faces
