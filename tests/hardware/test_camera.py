import cv2
from vision.camera import Camera

camera = Camera()

while True:

    frame = camera.get_frame()

    if frame is None:
        continue

    cv2.imshow("GreetBot Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
