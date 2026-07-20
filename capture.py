import cv2
import time

cap = cv2.VideoCapture(1, cv2.CAP_V4L2)

if not cap.isOpened():
    raise RuntimeError("Could not open camera")

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Let the webcam adjust
time.sleep(2)

# Throw away the first 20 frames
for _ in range(20):
    cap.read()

print("Press S to save, Q to quit.")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    cv2.imshow("Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("s"):
        cv2.imwrite("vision/faces/Komal.jpg", frame)
        print("Saved to vision/faces/Komal.jpg")
        break

    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
