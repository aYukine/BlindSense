import cv2

# Try opening the "good" device
cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("Cannot open /dev/video2")
    exit()

# Force a wide resolution - adjust these to your camera's max spec!
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    # Draw a vertical line down the exact middle
    cv2.line(frame, (w//2, 0), (w//2, h), (0, 0, 255), 2)
    
    cv2.imshow('Wide Stereo Frame (Red line is the split)', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
