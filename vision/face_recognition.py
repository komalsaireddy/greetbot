import os
import cv2
import numpy as np
import face_recognition


class FaceRecognition:

    def __init__(self, faces_dir="vision/faces"):

        self.faces_dir = faces_dir

        self.known_encodings = []
        self.known_names = []

        os.makedirs(self.faces_dir, exist_ok=True)

        self.load_faces()

    def load_faces(self):

        self.known_encodings.clear()
        self.known_names.clear()

        print("\nLoading known faces...")

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

                print(f"Loaded: {person_name}")

            else:

                if not item.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                image = face_recognition.load_image_file(path)

                encodings = face_recognition.face_encodings(image)

                if len(encodings) == 0:
                    print(f"Skipped {item} (no face detected)")
                    continue

                self.known_encodings.append(encodings[0])

                name = os.path.splitext(item)[0]

                self.known_names.append(name)

                print(f"Loaded: {name}")

        print(f"\nTotal Face Encodings Loaded: {len(self.known_encodings)}")

    def reload(self):

        self.load_faces()

    def recognize(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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

                if distances[best] < 0.48:

                    name = self.known_names[best]

                    confidence = (1 - distances[best]) * 100

            top, right, bottom, left = location

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
