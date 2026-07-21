"""
GreetBot Face Tracker
======================
Assigns stable IDs to detected faces across video frames using centroid
tracking. Prevents ID flicker when face_recognition briefly loses confidence
or misidentifies a face.
"""

from dataclasses import dataclass, field
from typing import Optional
import time

from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class TrackedFace:
    """Represents a face that is being tracked across frames."""
    track_id: int
    name: str
    confidence: float
    left: int
    top: int
    right: int
    bottom: int
    last_seen: float = field(default_factory=time.time)
    frames_visible: int = 1

    @property
    def center_x(self) -> int:
        return (self.left + self.right) // 2

    @property
    def center_y(self) -> int:
        return (self.top + self.bottom) // 2

    @property
    def center(self) -> tuple[int, int]:
        return (self.center_x, self.center_y)


class FaceTracker:
    """
    Centroid-based multi-face tracker.

    Matches incoming detections to existing tracks by Euclidean distance
    between face centers. Discards tracks that haven't been seen for
    *timeout* seconds.

    Parameters
    ----------
    max_distance:
        Maximum pixel distance between centroids to match a detection
        to an existing track.
    timeout:
        Seconds after which a track is considered lost.
    """

    def __init__(
        self,
        max_distance: int = 80,
        timeout: float = 3.0,
    ) -> None:
        self._tracks: dict[int, TrackedFace] = {}
        self._next_id: int = 1
        self._max_distance = max_distance
        self._timeout = timeout

    def update(self, detections: list[dict]) -> list[TrackedFace]:
        """
        Update tracks with new detections and return all active tracks.

        Matches each detection to the nearest existing track (if within
        *max_distance*). Unmatched detections become new tracks. Tracks
        not updated within *timeout* seconds are removed.

        Parameters
        ----------
        detections:
            List of face dicts from ``FaceRecognition.recognize()``.
            Each must have: ``name``, ``confidence``, ``left``, ``top``,
            ``right``, ``bottom``.

        Returns
        -------
        list[TrackedFace]
            All currently active tracks, updated with latest positions.
        """
        now = time.time()

        # ── Expire old tracks ─────────────────────────────────────────────────
        expired = [
            tid for tid, t in self._tracks.items()
            if now - t.last_seen > self._timeout
        ]
        for tid in expired:
            log.debug(f"Track expired: id={tid} name={self._tracks[tid].name!r}")
            del self._tracks[tid]

        if not detections:
            return list(self._tracks.values())

        # ── Match detections to tracks ────────────────────────────────────────
        matched_track_ids: set[int] = set()
        matched_detection_idxs: set[int] = set()

        for det_idx, det in enumerate(detections):
            det_cx = (det["left"] + det["right"]) // 2
            det_cy = (det["top"] + det["bottom"]) // 2

            best_tid: Optional[int] = None
            best_dist = float("inf")

            for tid, track in self._tracks.items():
                if tid in matched_track_ids:
                    continue
                dist = _euclidean(det_cx, det_cy, track.center_x, track.center_y)
                if dist < best_dist and dist < self._max_distance:
                    best_dist = dist
                    best_tid = tid

            if best_tid is not None:
                # Update existing track
                matched_track_ids.add(best_tid)
                matched_detection_idxs.add(det_idx)

                t = self._tracks[best_tid]
                t.left = det["left"]
                t.top = det["top"]
                t.right = det["right"]
                t.bottom = det["bottom"]
                t.last_seen = now
                t.frames_visible += 1

                # Only update name when confidence is higher (avoids flicker)
                if det["confidence"] > t.confidence or det["name"] != "Unknown":
                    t.name = det["name"]
                    t.confidence = det["confidence"]

        # ── Create new tracks for unmatched detections ────────────────────────
        for det_idx, det in enumerate(detections):
            if det_idx in matched_detection_idxs:
                continue

            new_track = TrackedFace(
                track_id=self._next_id,
                name=det["name"],
                confidence=det["confidence"],
                left=det["left"],
                top=det["top"],
                right=det["right"],
                bottom=det["bottom"],
            )
            self._tracks[self._next_id] = new_track
            log.debug(f"New track: id={self._next_id} name={det['name']!r}")
            self._next_id += 1

        return list(self._tracks.values())

    def clear(self) -> None:
        """Remove all active tracks."""
        self._tracks.clear()

    @property
    def track_count(self) -> int:
        """Number of currently active tracks."""
        return len(self._tracks)


def _euclidean(x1: int, y1: int, x2: int, y2: int) -> float:
    """Euclidean distance between two 2D points."""
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
