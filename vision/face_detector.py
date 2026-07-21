"""
GreetBot Face Detector
=======================
Fast pre-detection using OpenCV Haar Cascade.
Used as a cheap first pass before running the expensive face_recognition
encoder — dramatically reduces CPU load on Raspberry Pi.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

# Path to the OpenCV Haar cascade XML (bundled with opencv)
_CASCADE_PATH = (
    Path(cv2.__file__).parent / "data" / "haarcascade_frontalface_default.xml"
)


class FaceDetector:
    """
    Lightweight face detector using OpenCV Haar Cascade.

    Outputs bounding boxes only (no encodings). Designed to be used
    *before* FaceRecognition to skip frames with no faces quickly.

    Parameters
    ----------
    scale_factor:
        Image scale reduction factor per detection pyramid level.
    min_neighbors:
        Minimum neighbors required to retain a detection rectangle.
    min_size:
        Minimum face size in pixels (width, height).
    """

    def __init__(
        self,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: tuple[int, int] = (50, 50),
    ) -> None:
        if not _CASCADE_PATH.exists():
            log.warning(f"Haar cascade not found at {_CASCADE_PATH}. "
                        "FaceDetector will not pre-filter frames.")
            self._cascade: Optional[cv2.CascadeClassifier] = None
        else:
            self._cascade = cv2.CascadeClassifier(str(_CASCADE_PATH))
            log.info("FaceDetector ready (Haar cascade)")

        self._scale_factor = scale_factor
        self._min_neighbors = min_neighbors
        self._min_size = min_size

    def has_face(self, frame: np.ndarray) -> bool:
        """
        Quick check: does this frame contain at least one face?

        Parameters
        ----------
        frame:
            BGR frame from the camera.

        Returns
        -------
        bool
            True if one or more faces are detected.
        """
        return len(self.detect(frame)) > 0

    def detect(self, frame: np.ndarray) -> list[dict]:
        """
        Detect faces in a frame using the Haar cascade.

        Parameters
        ----------
        frame:
            BGR frame from the camera.

        Returns
        -------
        list[dict]
            Each dict has keys: ``left``, ``top``, ``right``, ``bottom``.
            Empty list if the cascade is unavailable or no faces found.
        """
        if self._cascade is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        detections = self._cascade.detectMultiScale(
            gray,
            scaleFactor=self._scale_factor,
            minNeighbors=self._min_neighbors,
            minSize=self._min_size,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if not isinstance(detections, np.ndarray) or len(detections) == 0:
            return []

        faces = []
        for x, y, w, h in detections:
            faces.append({
                "left":   int(x),
                "top":    int(y),
                "right":  int(x + w),
                "bottom": int(y + h),
            })

        return faces
