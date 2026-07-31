import cv2

from vision.camera import Camera
from vision.face_detector import FaceDetector

camera = Camera()
detector = FaceDetector()

while True:

    frame = camera.get_frame()

    if frame is None:
        continue

    faces = detector.detect(frame)

    for (x, y, w, h) in faces:

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

    cv2.imshow("GreetBot Vision", frame)

    if cv2.waitKey(1) == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
