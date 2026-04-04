import os
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
import cv2
import numpy as np
import cv2.ximgproc
from ament_index_python.packages import get_package_share_directory

class StereoPerceptionNode(Node):
    def __init__(self):
        super().__init__('stereo_perception_node')
        
        self.grid_pub = self.create_publisher(OccupancyGrid, 'hazard_map', 10)
        
        pkg_share_dir = get_package_share_directory('camera_pkg')
        calib_file = os.path.join(pkg_share_dir, 'config', 'stereoMap_.xml')
        self.get_logger().info(f"Loading calibration from: {calib_file}")
        self.load_rectification_maps(calib_file)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open stereo camera at index 0!")
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
        window_size = 5
        min_disp = 0
        num_disp = 16 * 8
        
        self.left_matcher = cv2.StereoSGBM_create(
            minDisparity=min_disp, numDisparities=num_disp, blockSize=window_size,
            P1=8 * 1 * window_size ** 2, P2=32 * 1 * window_size ** 2,
            disp12MaxDiff=1, uniquenessRatio=15, speckleWindowSize=100, speckleRange=32,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )
        self.right_matcher = cv2.ximgproc.createRightMatcher(self.left_matcher)
        
        self.wls_filter = cv2.ximgproc.createDisparityWLSFilter(matcher_left=self.left_matcher)
        self.wls_filter.setLambda(80000)
        self.wls_filter.setSigmaColor(1.5)

        # Tweak this
        self.resolution = 0.05       
        self.max_distance = 5.0      
        self.map_width = 4.0         
        
        self.grid_width = int(self.map_width / self.resolution)
        self.grid_height = int(self.max_distance / self.resolution)

        self.timer = self.create_timer(1.0 / 15.0, self.process_frames)
        self.get_logger().info("Unified Perception Engine Initialized.")

    def load_rectification_maps(self, filepath):
        cv_file = cv2.FileStorage(filepath, cv2.FILE_STORAGE_READ)
        self.mapL_x = cv_file.getNode('stereoMapL_x').mat()
        self.mapL_y = cv_file.getNode('stereoMapL_y').mat()
        self.mapR_x = cv_file.getNode('stereoMapR_x').mat()
        self.mapR_y = cv_file.getNode('stereoMapR_y').mat()
        self.Q = cv_file.getNode('q').mat() 
        cv_file.release()

    def process_frames(self):
        ret, sbs_frame = self.cap.read()
        if not ret:
            return

        half_width = sbs_frame.shape[1] // 2
        left_frame = sbs_frame[:, :half_width]
        right_frame = sbs_frame[:, half_width:]

        rect_left = cv2.remap(left_frame, self.mapL_x, self.mapL_y, cv2.INTER_LINEAR)
        rect_right = cv2.remap(right_frame, self.mapR_x, self.mapR_y, cv2.INTER_LINEAR)

        gray_left = cv2.cvtColor(rect_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(rect_right, cv2.COLOR_BGR2GRAY)

        disp_left = self.left_matcher.compute(gray_left, gray_right)
        disp_right = self.right_matcher.compute(gray_right, gray_left)
        
        filtered_disp = self.wls_filter.filter(disp_left, gray_left, None, disp_right)
        true_disp = filtered_disp.astype(np.float32) / 16.0
        
        true_disp[true_disp <= 0.0] = 0.1

        points_3D = cv2.reprojectImageTo3D(true_disp, self.Q) / 1000.0
        v = points_3D.reshape(-1, 3)

        valid_points = v[(v[:, 1] > -0.5) & (v[:, 1] < 0.5)]
        
        x = valid_points[:, 0]
        z = valid_points[:, 2]

        valid_dist = (z > 0.1) & (z < self.max_distance)
        x = x[valid_dist]
        z = z[valid_dist]

        grid_x = np.int32((x + (self.map_width / 2.0)) / self.resolution)
        grid_y = np.int32(z / self.resolution)

        in_bounds = (grid_x >= 0) & (grid_x < self.grid_width) & (grid_y >= 0) & (grid_y < self.grid_height)
        grid_x = grid_x[in_bounds]
        grid_y = grid_y[in_bounds]

        occupancy_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
        
        occupancy_grid[grid_y, grid_x] = 100

        kernel = np.ones((3,3), np.uint8)
        occupancy_grid = cv2.dilate(occupancy_grid, kernel, iterations=1)

        grid_msg = OccupancyGrid()
        grid_msg.header.stamp = self.get_clock().now().to_msg()
        grid_msg.header.frame_id = "camera_link"
        
        grid_msg.info.resolution = self.resolution
        grid_msg.info.width = self.grid_width
        grid_msg.info.height = self.grid_height
        
        grid_msg.info.origin.position.x = -(self.map_width / 2.0)
        grid_msg.info.origin.position.y = 0.0
        grid_msg.info.origin.position.z = 0.0
        
        grid_msg.data = occupancy_grid.astype(np.int8).flatten().tolist()
        
        self.grid_pub.publish(grid_msg)

    def destroy_node(self):
        self.get_logger().info("Releasing camera...")
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = StereoPerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()