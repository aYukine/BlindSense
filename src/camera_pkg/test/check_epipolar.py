import cv2
import numpy as np

# 1. Load your newly generated calibration maps
xml_path = '/home/rith/Documents/BlindSense/src/camera_pkg/stereoMap.xml' # Update if needed!
cv_file = cv2.FileStorage(xml_path, cv2.FILE_STORAGE_READ)

if not cv_file.isOpened():
    print(f"CRITICAL ERROR: Could not open {xml_path}")
    exit()

mapL_x = cv_file.getNode('stereoMapL_x').mat()
mapL_y = cv_file.getNode('stereoMapL_y').mat()
mapR_x = cv_file.getNode('stereoMapR_x').mat()
mapR_y = cv_file.getNode('stereoMapR_y').mat()
cv_file.release()

# 2. Start the camera using our fast GStreamer pipeline
gstreamer_pipeline = (
    "v4l2src device=/dev/video2 ! "
    "image/jpeg,width=1280,height=480,framerate=30/1 ! "
    "jpegdec ! videoconvert ! video/x-raw,format=BGR ! "
    "appsink drop=true sync=false max-buffers=1"
)
cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)

print("Starting Epipolar Check... Press ESC to close the window.")

while True:
    ret, frame = cap.read()
    if not ret: 
        print("Dropped frame!")
        continue

    # Split the hardware frame
    left = frame[:, :640]
    right = frame[:, 640:]

    # Apply the calibration math to physically flatten the images
    left_rect = cv2.remap(left, mapL_x, mapL_y, cv2.INTER_LINEAR)
    right_rect = cv2.remap(right, mapR_x, mapR_y, cv2.INTER_LINEAR)

    # Glue them back together side-by-side
    combined = np.hstack((left_rect, right_rect))

    # Draw laser-straight green horizontal lines across both feeds
    for y in range(0, 480, 40):
        cv2.line(combined, (0, y), (1280, y), (0, 255, 0), 1)

    cv2.imshow('Epipolar Alignment Check', combined)
    
    if cv2.waitKey(1) == 27: # Press ESC to quit
        break

cap.release()
cv2.destroyAllWindows()