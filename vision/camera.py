import cv2


class Camera:

    def __init__(self):

        self.cap = cv2.VideoCapture(1, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")

        # Use MJPEG
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Buffer size
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def get_frame(self):

        ret, frame = self.cap.read()

        if not ret:
            return None

        return frame

    def release(self):
        self.cap.release()
