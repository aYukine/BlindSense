import numpy as np
import cv2

# 1. Load Calibration Maps
cv_file = cv2.FileStorage()
cv_file.open('stereoMap.xml', cv2.FileStorage_READ)

stereoMapL_x = cv_file.getNode('stereoMapL_x').mat()
stereoMapL_y = cv_file.getNode('stereoMapL_y').mat()
stereoMapR_x = cv_file.getNode('stereoMapR_x').mat()
stereoMapR_y = cv_file.getNode('stereoMapR_y').mat()
cv_file.release()

# 2. Open Camera
cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# 3. Configure the SGBM Matcher
window_size = 5
min_disp = 0
num_disp = 16 * 10 # Must be divisible by 16. Higher means it can see closer objects.

# Create the Left Matcher
left_matcher = cv2.StereoSGBM_create(
    minDisparity=min_disp,
    numDisparities=num_disp,
    blockSize=window_size,
    P1=8 * 3 * window_size ** 2,
    P2=32 * 3 * window_size ** 2,
    disp12MaxDiff=1,
    uniquenessRatio=15,
    speckleWindowSize=100,
    speckleRange=32,
    mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
)

right_matcher = cv2.ximgproc.createRightMatcher(left_matcher)

wls_filter = cv2.ximgproc.createDisparityWLSFilter(matcher_left=left_matcher)
wls_filter.setLambda(8000) 
wls_filter.setSigmaColor(1.5) 
print("Streaming High-Quality Depth. Press 'q' to quit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    half_width = frame.shape[1] // 2
    frame_left = frame[:, :half_width]
    frame_right = frame[:, half_width:]

    rect_left = cv2.remap(frame_left, stereoMapL_x, stereoMapL_y, cv2.INTER_LANCZOS4, cv2.BORDER_CONSTANT, 0)
    rect_right = cv2.remap(frame_right, stereoMapR_x, stereoMapR_y, cv2.INTER_LANCZOS4, cv2.BORDER_CONSTANT, 0)

    gray_left = cv2.cvtColor(rect_left, cv2.COLOR_BGR2GRAY)
    gray_right = cv2.cvtColor(rect_right, cv2.COLOR_BGR2GRAY)

    disp_left = left_matcher.compute(gray_left, gray_right)
    disp_right = right_matcher.compute(gray_right, gray_left)

    filtered_disp = wls_filter.filter(disp_left, gray_left, None, disp_right)

    filtered_disp_vis = cv2.normalize(filtered_disp, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    depth_colormap = cv2.applyColorMap(filtered_disp_vis, cv2.COLORMAP_JET)

    display_scale = 0.5
    left_resized = cv2.resize(rect_left, (0,0), fx=display_scale, fy=display_scale)
    depth_resized = cv2.resize(depth_colormap, (0,0), fx=display_scale, fy=display_scale)

    combined_view = np.hstack((left_resized, depth_resized))
    cv2.imshow("Left RGB | Filtered Depth Map", combined_view)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()