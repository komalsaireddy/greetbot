import os
import re
import cv2
import json
import time
from datetime import datetime


class PersonRegistration:

    def __init__(self):

        self.faces_dir = "vision/faces"
        self.memory_dir = "memory"

        os.makedirs(self.faces_dir, exist_ok=True)
        os.makedirs(self.memory_dir, exist_ok=True)

    def extract_name(self, text):

        text = text.strip()

        patterns = [
            r"my name is (.+)",
            r"i am (.+)",
            r"i'm (.+)",
            r"this is (.+)"
        ]

        for pattern in patterns:

            match = re.search(pattern, text.lower())

            if match:

                name = match.group(1).strip()

                name = name.title()

                name = re.sub(r"[^A-Za-z ]", "", name)

                return name

        return text.title()

    def create_profile(self, name):

        profile = {

            "name": name,

            "first_seen": datetime.now().isoformat(),

            "last_seen": datetime.now().isoformat(),

            "visit_count": 1,

            "college": None,

            "profession": None,

            "city": None,

            "hobbies": [],

            "pets": [],

            "preferences": {},

            "conversation_summary": []

        }

        with open(
            os.path.join(
                self.memory_dir,
                f"{name}.json"
            ),
            "w"
        ) as f:

            json.dump(
                profile,
                f,
                indent=4
            )

    def capture_faces(self, camera, frame, face, name):

        folder = os.path.join(
            self.faces_dir,
            name
        )

        os.makedirs(folder, exist_ok=True)

        left = max(face["left"], 0)
        top = max(face["top"], 0)
        right = min(face["right"], frame.shape[1])
        bottom = min(face["bottom"], frame.shape[0])

        count = 0

        while count < 10:

            frame = camera.get_frame()

            if frame is None:
                continue

            crop = frame[
                top:bottom,
                left:right
            ]

            if crop.size == 0:
                continue

            cv2.imwrite(

                os.path.join(
                    folder,
                    f"{count+1}.jpg"
                ),

                crop

            )

            count += 1

            time.sleep(0.2)

        print(f"Saved {count} face images for {name}")

    def register(self,
                 camera,
                 frame,
                 face,
                 spoken_text):

        name = self.extract_name(
            spoken_text
        )

        print(
            f"Registering new person: {name}"
        )

        self.capture_faces(
            camera,
            frame,
            face,
            name
        )

        self.create_profile(
            name
        )

        return name
