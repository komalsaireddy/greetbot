import json
import os
from datetime import datetime


class ProfileManager:

    def __init__(self):

        self.memory_dir = "memory"

        os.makedirs(self.memory_dir, exist_ok=True)

    def profile_path(self, person_id):

        return os.path.join(
            self.memory_dir,
            f"{person_id}.json"
        )

    def exists(self, person_id):

        return os.path.exists(
            self.profile_path(person_id)
        )

    def create(self, person_id):

        if self.exists(person_id):
            return

        profile = {
            "id": person_id,
            "name": None,
            "age": None,
            "college": None,
            "profession": None,
            "city": None,
            "hobbies": [],
            "pets": [],
            "preferences": {},
            "conversation_summary": [],
            "visit_count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }

        self.save(person_id, profile)

    def load(self, person_id):

        if not self.exists(person_id):
            self.create(person_id)

        with open(self.profile_path(person_id), "r") as f:
            return json.load(f)

    def save(self, person_id, profile):

        profile["last_seen"] = datetime.now().isoformat()

        with open(self.profile_path(person_id), "w") as f:
            json.dump(profile, f, indent=4)

    def update(self, person_id, key, value):

        profile = self.load(person_id)

        profile[key] = value

        self.save(person_id, profile)

    def increment_visit(self, person_id):

        profile = self.load(person_id)

        profile["visit_count"] += 1

        self.save(person_id, profile)

    def rename(self, old_id, new_name):

        old_json = self.profile_path(old_id)

        new_json = self.profile_path(new_name)

        if not os.path.exists(old_json):
            return

        profile = self.load(old_id)

        profile["id"] = new_name
        profile["name"] = new_name

        with open(new_json, "w") as f:
            json.dump(profile, f, indent=4)

        os.remove(old_json)
