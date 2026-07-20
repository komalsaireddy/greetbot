import time


class Perception:

    def __init__(self):

        self.people = {}
        self.timeout = 20.0

    def update(self, faces):

        now = time.time()

        # Update detected faces
        for face in faces:

            left = face["left"]
            right = face["right"]
            top = face["top"]
            bottom = face["bottom"]

            center_x = (left + right) // 2
            center_y = (top + bottom) // 2

            self.people[face["name"]] = {

                "name": face["name"],
                "confidence": face["confidence"],
                "left": left,
                "right": right,
                "top": top,
                "bottom": bottom,
                "center": (center_x, center_y),
                "last_seen": now

            }

        # Remove people not seen recently
        expired = []

        for name, person in self.people.items():

            if now - person["last_seen"] > self.timeout:
                expired.append(name)

        for name in expired:
            del self.people[name]

    def get_people(self):

        return list(self.people.values())

    def get_known_people(self):

        return [

            p for p in self.people.values()

            if p["name"] != "Unknown"

        ]

    def get_unknown_people(self):

        return [

            p for p in self.people.values()

            if p["name"] == "Unknown"

        ]

    def person_count(self):

        return len(self.people)

    def known_count(self):

        return len(self.get_known_people())

    def unknown_count(self):

        return len(self.get_unknown_people())

    def is_visible(self, name):

        return name in self.people

    def get_state(self):

        return {

            "people": self.get_people(),
            "person_count": self.person_count(),
            "known_count": self.known_count(),
            "unknown_count": self.unknown_count()

        }
