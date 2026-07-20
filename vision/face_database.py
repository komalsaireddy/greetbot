import os
import cv2

from memory.profile_manager import ProfileManager


class FaceDatabase:

    def __init__(self):

        self.face_dir = "vision/faces"

        os.makedirs(self.face_dir, exist_ok=True)

        self.profile = ProfileManager()

    def next_person_id(self):

        ids = []

        for file in os.listdir(self.face_dir):

            if not file.startswith("person_"):
                continue

            name = file.split(".")[0]

            try:
                ids.append(int(name.split("_")[1]))
            except:
                pass

        if not ids:
            return "person_001"

        return f"person_{max(ids)+1:03d}"

    def save_unknown_face(self, frame, face):

        person_id = self.next_person_id()

        left = max(face["left"], 0)
        top = max(face["top"], 0)
        right = min(face["right"], frame.shape[1])
        bottom = min(face["bottom"], frame.shape[0])

        crop = frame[top:bottom, left:right]

        if crop.size == 0:
            return None

        filename = os.path.join(
            self.face_dir,
            person_id + ".jpg"
        )

        cv2.imwrite(filename, crop)

        self.profile.create(person_id)

        print(f"Saved new person: {person_id}")

        return person_id
