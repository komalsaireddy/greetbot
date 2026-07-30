"""Regression tests for hardware-independent GreetBot behavior."""

import tempfile
import unittest
from pathlib import Path
from types import ModuleType
import sys

# Keep these hardware-independent tests runnable before the optional project
# dependencies have been installed on a developer workstation.
if "dotenv" not in sys.modules:
    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: False
    sys.modules["dotenv"] = dotenv

from memory.database import Database
from memory.profile_manager import ProfileManager
from vision.face_tracking import FaceTracker


class ProfileManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._temp_dir.name) / "greetbot.db")
        self.profiles = ProfileManager(db=self.db)

    def tearDown(self) -> None:
        self.db.close()
        self._temp_dir.cleanup()

    def test_known_person_has_a_profile_before_conversation_is_saved(self) -> None:
        profile = self.profiles.get_or_create("Komal")
        self.db.add_conversation_turn(profile["id"], "user", "Hello")

        self.assertEqual(profile["id"], "komal")
        turns = self.db.get_last_n_turns("komal")
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["role"], "user")
        self.assertEqual(turns[0]["content"], "Hello")

    def test_returning_person_visit_is_incremented(self) -> None:
        profile = self.profiles.get_or_create("Komal")
        self.profiles.update_last_seen(profile["id"])

        self.assertEqual(self.profiles.load(profile["id"])["visit_count"], 2)


class FaceTrackerTests(unittest.TestCase):
    def test_track_is_retained_briefly_between_recognition_passes(self) -> None:
        tracker = FaceTracker(timeout=1)
        tracks = tracker.update([
            {"name": "Komal", "confidence": 90, "left": 10, "top": 10, "right": 50, "bottom": 50}
        ])

        retained = tracker.update([])

        self.assertEqual(len(tracks), 1)
        self.assertEqual(retained[0].track_id, tracks[0].track_id)
        self.assertEqual(retained[0].name, "Komal")


if __name__ == "__main__":
    unittest.main()
