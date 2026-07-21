"""
GreetBot Face Database
=======================
Manages the on-disk face image store and links face images to person profiles.
Supports saving unknown faces, registering known persons, and reloading
the recognition model after new faces are added.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import VISION_FACES_DIR
from memory.profile_manager import ProfileManager
from memory.database import Database
from utils.logger import get_logger

log = get_logger(__name__)


class FaceDatabase:
    """
    Manages face images on disk and their associated person profiles.

    Face images are stored in ``vision/faces/<name>/`` folders.
    Unknown faces are saved temporarily as ``vision/faces/person_001.jpg``
    (flat files) until the person is registered with a name.

    Parameters
    ----------
    db:
        Shared Database instance. If None, a new one is created.
    """

    def __init__(self, db: Optional[Database] = None) -> None:
        self._db = db or Database()
        self._profiles = ProfileManager(db=self._db)
        self._faces_dir = Path(VISION_FACES_DIR)
        self._faces_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"FaceDatabase ready (dir={self._faces_dir})")

    # ── Unknown Face Handling ─────────────────────────────────────────────────

    def next_person_id(self) -> str:
        """
        Generate the next sequential ``person_NNN`` ID.

        Scans the face directory for existing ``person_*`` entries to
        determine the next number.

        Returns
        -------
        str
            e.g. ``"person_003"``.
        """
        ids: list[int] = []

        for entry in self._faces_dir.iterdir():
            name = entry.stem if entry.is_file() else entry.name
            if name.startswith("person_"):
                try:
                    ids.append(int(name.split("_")[1]))
                except (IndexError, ValueError):
                    pass

        next_num = max(ids, default=0) + 1
        return f"person_{next_num:03d}"

    def save_unknown_face(self, frame: np.ndarray, face: dict) -> Optional[str]:
        """
        Crop and save an unknown face image, creating a provisional profile.

        Parameters
        ----------
        frame:
            Full camera frame (BGR).
        face:
            Face detection dict with ``left``, ``top``, ``right``, ``bottom``.

        Returns
        -------
        str or None
            Assigned ``person_NNN`` ID, or None if the crop was empty.
        """
        person_id = self.next_person_id()

        left   = max(face["left"],   0)
        top    = max(face["top"],    0)
        right  = min(face["right"],  frame.shape[1])
        bottom = min(face["bottom"], frame.shape[0])

        crop = frame[top:bottom, left:right]
        if crop.size == 0:
            log.warning("save_unknown_face: empty crop, skipping")
            return None

        filename = self._faces_dir / f"{person_id}.jpg"
        cv2.imwrite(str(filename), crop)

        # Create a provisional profile
        self._profiles.create(person_id=person_id)

        log.info(f"Saved unknown face: {person_id}")
        return person_id

    # ── Known Person Registration ─────────────────────────────────────────────

    def register_person(
        self,
        name: str,
        frame: np.ndarray,
        face: dict,
        n_captures: int = 10,
        camera=None,
    ) -> str:
        """
        Register a new known person by saving multiple face crops.

        Creates a folder ``vision/faces/<name>/`` and saves *n_captures*
        images of the face. Also creates or updates the person's profile.

        Parameters
        ----------
        name:
            Display name for the person.
        frame:
            Current camera frame (BGR) — used for the first crop.
        face:
            Face detection dict.
        n_captures:
            Number of face images to capture (more = better accuracy).
        camera:
            Optional Camera instance to capture additional frames.

        Returns
        -------
        str
            The person's profile ID.
        """
        from utils.helpers import normalize_name
        clean_name = normalize_name(name)
        folder = self._faces_dir / clean_name
        folder.mkdir(parents=True, exist_ok=True)

        left   = max(face["left"],   0)
        top    = max(face["top"],    0)
        right  = min(face["right"],  frame.shape[1])
        bottom = min(face["bottom"], frame.shape[0])

        count = 0

        # Save the first frame immediately
        crop = frame[top:bottom, left:right]
        if crop.size > 0:
            cv2.imwrite(str(folder / f"1.jpg"), crop)
            count += 1

        # Optionally capture more frames
        if camera and n_captures > 1:
            import time
            while count < n_captures:
                f = camera.get_frame()
                if f is None:
                    continue
                crop = f[top:bottom, left:right]
                if crop.size == 0:
                    continue
                cv2.imwrite(str(folder / f"{count + 1}.jpg"), crop)
                count += 1
                time.sleep(0.15)

        # Create or update profile
        profile = self._profiles.get_or_create(clean_name)
        log.info(f"Registered person: {clean_name} ({count} face images)")
        return profile["id"]

    def delete_person(self, name: str) -> None:
        """
        Delete a person's face images and profile from the database.

        Parameters
        ----------
        name:
            Display name of the person to delete.
        """
        import shutil
        from utils.helpers import normalize_name

        clean = normalize_name(name)
        folder = self._faces_dir / clean

        if folder.exists():
            shutil.rmtree(folder)
            log.info(f"Deleted face folder: {folder}")

        # Also delete flat file if it exists
        flat = self._faces_dir / f"{clean}.jpg"
        if flat.exists():
            flat.unlink()

        # Delete profile
        person_id = clean.lower().replace(" ", "_")
        self._profiles.delete(person_id)

    def list_known_persons(self) -> list[str]:
        """
        Return names of all persons with stored face images.

        Returns
        -------
        list[str]
            Folder names (= person names) under the faces directory.
        """
        names = []
        for entry in sorted(self._faces_dir.iterdir()):
            if entry.is_dir():
                names.append(entry.name)
        return names
