import rclpy
import numpy as np
import cv2
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from rclpy.qos import QoSProfile, ReliabilityPolicy
import os
from ament_index_python.packages import get_package_share_directory

class StereoDepthNode(Node):
    def __init__(self):
        super().__init__('depth_node')
        self.get_logger().info('stereo depth node started.')
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=1
        )
        self.timer = self.create_timer(0.1, self.capture_depth)
        self.image_publisher = self.create_publisher(CompressedImage, 'camera/image/compressed', qos_profile)
        self.setup_cam()

    def setup_cam(self):    
        try:
            package_share_dir = get_package_share_directory('camera_pkg')
            xml_path = os.path.join(package_share_dir, 'config', 'stereoMap.xml')
            self.get_logger().info(f'Loading calibration from: {xml_path}')
        except Exception as e:
            self.get_logger().error(f'Failed to find package directory: {e}')
            return

        cv_file = cv2.FileStorage()
        if not cv_file.open(xml_path, cv2.FileStorage_READ):
            self.get_logger().error('Could not open stereoMap.xml!')
            return

        self.stereoMapL_x = cv_file.getNode('stereoMapL_x').mat()
        self.stereoMapL_y = cv_file.getNode('stereoMapL_y').mat()
        self.stereoMapR_x = cv_file.getNode('stereoMapR_x').mat()
        self.stereoMapR_y = cv_file.getNode('stereoMapR_y').mat()
        cv_file.release()

        self.cap = cv2.VideoCapture(2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        window_size = 5
        min_disp = 0
        num_disp = 16 * 10 # Must be divisible by 16. Higher means it can see closer objects.

        # Create the Left Matcher
        self.left_matcher = cv2.StereoSGBM_create(
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

        self.right_matcher = cv2.ximgproc.createRightMatcher(self.left_matcher)
        self.wls_filter = cv2.ximgproc.createDisparityWLSFilter(matcher_left=self.left_matcher)
        self.wls_filter.setLambda(8000) 
        self.wls_filter.setSigmaColor(1.5) 

    def capture_depth(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().error('fail to capture camera')

        half_width = frame.shape[1] // 2
        frame_left = frame[:, :half_width]
        frame_right = frame[:, half_width:]

        rect_left = cv2.remap(frame_left, self.stereoMapL_x, self.stereoMapL_y, cv2.INTER_LANCZOS4, cv2.BORDER_CONSTANT, 0)
        rect_right = cv2.remap(frame_right, self.stereoMapR_x, self.stereoMapR_y, cv2.INTER_LANCZOS4, cv2.BORDER_CONSTANT, 0)

        gray_left = cv2.cvtColor(rect_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(rect_right, cv2.COLOR_BGR2GRAY)

        disp_left = self.left_matcher.compute(gray_left, gray_right)
        disp_right = self.right_matcher.compute(gray_right, gray_left)

        filtered_disp = self.wls_filter.filter(disp_left, gray_left, None, disp_right)

        filtered_disp_vis = cv2.normalize(filtered_disp, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        depth_colormap = cv2.applyColorMap(filtered_disp_vis, cv2.COLORMAP_JET)

        small_frame = cv2.resize(depth_colormap, (640, 360)) 
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.format = "jpeg"
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 20]
        success, encoded_image = cv2.imencode('.jpg', small_frame, encode_param)

        if success:
            msg.data = encoded_image.tobytes()
            self.image_publisher.publish(msg)
        
    

def main(args=None):
    rclpy.init(args=args)
    camera_node = StereoDepthNode()
    try:
        rclpy.spin(camera_node)
    except KeyboardInterrupt:
        pass
    finally:
        camera_node.cap.release()
        camera_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()