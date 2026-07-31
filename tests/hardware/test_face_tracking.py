import cv2

from vision.camera import Camera
from vision.face_detector import FaceDetector
from vision.face_tracking import FaceTracker

camera = Camera()
detector = FaceDetector()
tracker = FaceTracker()

while True:

    frame = camera.get_frame()

    if frame is None:
        continue

    faces = detector.detect(frame)

    face = tracker.get_primary_face(faces)

    if face is not None:

        x, y, w, h = face

        cx, cy = tracker.get_face_center(face)

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)

        cv2.circle(frame, (cx, cy), 5, (0,0,255), -1)

        print(f"Face Center: ({cx}, {cy})", end="\r")

    cv2.imshow("Face Tracking", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
