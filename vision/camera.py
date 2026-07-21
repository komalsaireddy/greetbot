"""
GreetBot Camera
===============
Wraps OpenCV video capture with platform-aware backend selection,
configurable resolution, and frame-skip support for CPU efficiency.
"""

import sys
import cv2
import numpy as np
from typing import Optional

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAMERA_RECOGNITION_SKIP,
    IS_LINUX,
)
from utils.logger import get_logger

log = get_logger(__name__)


class Camera:
    """
    Thread-safe camera wrapper.

    Chooses the appropriate OpenCV backend automatically:
    - Linux / Raspberry Pi: ``CAP_V4L2`` for low-latency capture
    - macOS / other: default backend

    Parameters
    ----------
    index:
        Camera device index. Defaults to ``CAMERA_INDEX`` from config.
    width:
        Requested capture width in pixels.
    height:
        Requested capture height in pixels.
    """

    def __init__(
        self,
        index: Optional[int] = None,
        width: int = CAMERA_WIDTH,
        height: int = CAMERA_HEIGHT,
    ) -> None:
        cam_index = index if index is not None else CAMERA_INDEX

        log.info(f"Opening camera index={cam_index} ({width}×{height})")

        if IS_LINUX:
            self._cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)
        else:
            self._cap = cv2.VideoCapture(cam_index)

        if not self._cap.isOpened():
            log.error(f"Could not open camera at index {cam_index}")
            raise RuntimeError(
                f"Camera not available at index {cam_index}. "
                "Check the CAMERA_INDEX in config.py."
            )

        # Prefer MJPEG for lower latency on USB cameras
        self._cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"MJPG")  # type: ignore[attr-defined]
        )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        log.info(f"Camera opened: {actual_w}×{actual_h}")

        self._frame_count: int = 0
        self._skip: int = CAMERA_RECOGNITION_SKIP

    # ── Frame Access ──────────────────────────────────────────────────────────

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Grab and return the latest frame from the camera.

        Returns
        -------
        numpy.ndarray or None
            BGR image array, or None if the frame could not be read.
        """
        ret, frame = self._cap.read()
        if not ret or frame is None:
            log.debug("Camera: failed to read frame")
            return None

        self._frame_count += 1
        return frame

    def should_run_recognition(self) -> bool:
        """
        Return True every N frames to gate expensive face recognition.

        This allows the camera to run at full FPS while only doing the
        expensive recognition pass every ``CAMERA_RECOGNITION_SKIP`` frames.

        Returns
        -------
        bool
            True if recognition should run on the current frame.
        """
        return (self._frame_count % (self._skip + 1)) == 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def release(self) -> None:
        """Release the camera resource."""
        if self._cap.isOpened():
            self._cap.release()
            log.info("Camera released")

    def is_open(self) -> bool:
        """Return True if the camera is currently open."""
        return self._cap.isOpened()

    @property
    def frame_count(self) -> int:
        """Total frames captured since camera was opened."""
        return self._frame_count

    def __del__(self) -> None:
        self.release()
