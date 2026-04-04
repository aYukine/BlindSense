import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import cv2.ximgproc
from ament_index_python.packages import get_package_share_directory

class StereoDepthNode(Node):
    def __init__(self):
        super().__init__('stereo_depth_node')
        
        # Publisher and Bridge
        self.depth_pub = self.create_publisher(Image, 'stereo/depth', 10)
        self.disparity_pub = self.create_publisher(Image, 'stereo/disparity_filtered', 10)
        self.bridge = CvBridge()
        
        # Locate and Load the Calibration XML
        pkg_share_dir = get_package_share_directory('camera_pkg')
        calib_file = os.path.join(pkg_share_dir, 'config', 'stereoMap.xml')
        self.get_logger().info(f"Loading calibration from: {calib_file}")
        self.load_rectification_maps(calib_file)

        # Initialize the SBS Stereo Camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open stereo camera at index 0!")
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.get_logger().info(f"Camera initialized at: {actual_width}x{actual_height} @ {actual_fps}FPS")

        # SGBM Parameters 
        window_size = 5
        min_disp = 0
        num_disp = 16 * 10

        # The Left Matcher (Primary SGBM)
        self.left_matcher = cv2.StereoSGBM_create(
            minDisparity=min_disp,
            numDisparities=num_disp,
            blockSize=window_size,
            P1=8 * 1 * window_size ** 2,   
            P2=32 * 1 * window_size ** 2,  
            disp12MaxDiff=1,
            uniquenessRatio=15,
            speckleWindowSize=100,
            speckleRange=32,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )

        # The Right Matcher (Required for WLS)
        self.right_matcher = cv2.ximgproc.createRightMatcher(self.left_matcher)
        
        self.wls_filter = cv2.ximgproc.createDisparityWLSFilter(matcher_left=self.left_matcher)
        self.wls_filter.setLambda(8000)
        self.wls_filter.setSigmaColor(1.5)
        
        # Replace with your actual hardware constants from calibration
        self.focal_length = 800.0 
        self.baseline = 0.06 
        
        # Timer matching your 15-30 frames per second target
        self.timer = self.create_timer(1.0 / 15.0, self.process_frames)
        self.get_logger().info("Stereo Depth Node Initialized and Publishing.")

    def load_rectification_maps(self, filepath):
        """Extracts the X and Y maps for both lenses from the XML file."""
        cv_file = cv2.FileStorage(filepath, cv2.FILE_STORAGE_READ)
        
        self.mapL_x = cv_file.getNode('stereoMapL_x').mat()
        self.mapL_y = cv_file.getNode('stereoMapL_y').mat()
        self.mapR_x = cv_file.getNode('stereoMapR_x').mat()
        self.mapR_y = cv_file.getNode('stereoMapR_y').mat()
        
        cv_file.release()
        
        if self.mapL_x is None:
            self.get_logger().error("Failed to load maps! Check XML key names.")

    def process_frames(self):
        # Capture the single SBS frame
        ret, sbs_frame = self.cap.read()
        if not ret:
            self.get_logger().warn("Dropped frame from stereo camera.")
            return

        # Slice the frame down the middle
        mid_point = sbs_frame.shape[1] // 2 
        left_frame = sbs_frame[:, :mid_point] 
        right_frame = sbs_frame[:, mid_point:] 

        # Apply the rectification maps
        rectified_L = cv2.remap(left_frame, self.mapL_x, self.mapL_y, cv2.INTER_LINEAR)
        rectified_R = cv2.remap(right_frame, self.mapR_x, self.mapR_y, cv2.INTER_LINEAR)

        # Convert to grayscale for SGBM
        left_gray = cv2.cvtColor(rectified_L, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(rectified_R, cv2.COLOR_BGR2GRAY)

        # Compute Left and Right Disparities
        disp_left = self.left_matcher.compute(left_gray, right_gray)
        disp_right = self.right_matcher.compute(right_gray, left_gray)

        # Apply the WLS Filter
        filtered_disp = self.wls_filter.filter(disp_left, left_gray, None, disp_right)

        # Convert to Depth
        disparity = filtered_disp.astype(np.float32) / 16.0

        disparity[disparity <= 0] = 0.1 

        depth = (self.focal_length * self.baseline) / disparity
        depth[depth > 5.0] = 5.0  # Cap max distance at 5 meters

        # Publish to ROS 2
        depth_msg = self.bridge.cv2_to_imgmsg(depth, encoding="32FC1")
        depth_msg.header.stamp = self.get_clock().now().to_msg()
        depth_msg.header.frame_id = "camera_link" 

        self.depth_pub.publish(depth_msg)
        
        # Prevent divide-by-zero on invalid pixels
        disparity[disparity <= 0] = 0.1 

        depth = (self.focal_length * self.baseline) / disparity
        depth[depth > 5.0] = 5.0  # Cap max distance at 5 meters

        # Publish to ROS 2
        depth_msg = self.bridge.cv2_to_imgmsg(depth, encoding="32FC1")
        depth_msg.header.stamp = self.get_clock().now().to_msg()
        depth_msg.header.frame_id = "camera_link" 
        
        self.depth_pub.publish(depth_msg)

    def destroy_node(self):
        self.get_logger().info("Shutting down and releasing camera...")
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = StereoDepthNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Keyboard Interrupt detected.")
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()