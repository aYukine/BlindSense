import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from nav_msgs.msg import OccupancyGrid
import message_filters
import cv2
import numpy as np
import cv2.ximgproc
from ament_index_python.packages import get_package_share_directory

class StereoPerceptionNode(Node):
    def __init__(self):
        super().__init__('stereo_perception_node')
        
        self.grid_pub = self.create_publisher(OccupancyGrid, 'hazard_map', 10)
        
        # 1. Subscribe to ALL THREE topics
        self.left_sub = message_filters.Subscriber(self, Image, 'camera/left/image_raw')
        self.right_sub = message_filters.Subscriber(self, Image, 'camera/right/image_raw')
        self.mask_sub = message_filters.Subscriber(self, Image, 'perception/walkable_mask')
        
        # 2. Synchronize all three so we only process when we have matching frames
        self.ts = message_filters.TimeSynchronizer([self.left_sub, self.right_sub, self.mask_sub], queue_size=10)
        self.ts.registerCallback(self.process_fused_frames)
        
        pkg_share_dir = get_package_share_directory('camera_pkg')
        calib_file = os.path.join(pkg_share_dir, 'config', 'stereoMap_.xml')
        self.load_rectification_maps(calib_file)

        window_size = 5
        self.left_matcher = cv2.StereoSGBM_create(
            minDisparity=0, numDisparities=128, blockSize=window_size,
            P1=8 * 1 * window_size ** 2, P2=32 * 1 * window_size ** 2,
            disp12MaxDiff=1, uniquenessRatio=15, speckleWindowSize=100, speckleRange=32,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )
        self.right_matcher = cv2.ximgproc.createRightMatcher(self.left_matcher)
        self.wls_filter = cv2.ximgproc.createDisparityWLSFilter(matcher_left=self.left_matcher)
        self.wls_filter.setLambda(80000)
        self.wls_filter.setSigmaColor(1.5)

        self.resolution = 0.05       
        self.max_distance = 5.0      
        self.map_width = 4.0         
        self.grid_width = int(self.map_width / self.resolution)
        self.grid_height = int(self.max_distance / self.resolution)

        self.get_logger().info("Sensor Fusion Engine Initialized. Waiting for synced topics...")

    def load_rectification_maps(self, filepath):
        cv_file = cv2.FileStorage(filepath, cv2.FILE_STORAGE_READ)
        self.mapL_x = cv_file.getNode('stereoMapL_x').mat()
        self.mapL_y = cv_file.getNode('stereoMapL_y').mat()
        self.mapR_x = cv_file.getNode('stereoMapR_x').mat()
        self.mapR_y = cv_file.getNode('stereoMapR_y').mat()
        self.Q = cv_file.getNode('q').mat() 
        cv_file.release()

    def process_fused_frames(self, left_msg: Image, right_msg: Image, mask_msg: Image):
        # Convert ROS messages to numpy arrays
        left_frame = np.frombuffer(left_msg.data, dtype=np.uint8).reshape((left_msg.height, left_msg.width, 3))
        right_frame = np.frombuffer(right_msg.data, dtype=np.uint8).reshape((right_msg.height, right_msg.width, 3))
        
        # The AI mask is 1-channel (mono8)
        mask_img = np.frombuffer(mask_msg.data, dtype=np.uint8).reshape((mask_msg.height, mask_msg.width))

        # Rectify the images AND the mask so they all align perfectly
        rect_left = cv2.remap(left_frame, self.mapL_x, self.mapL_y, cv2.INTER_LINEAR)
        rect_right = cv2.remap(right_frame, self.mapR_x, self.mapR_y, cv2.INTER_LINEAR)
        rect_mask = cv2.remap(mask_img, self.mapL_x, self.mapL_y, cv2.INTER_NEAREST) # Nearest neighbor for masks

        gray_left = cv2.cvtColor(rect_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(rect_right, cv2.COLOR_BGR2GRAY)

        # Compute Depth
        disp_left = self.left_matcher.compute(gray_left, gray_right)
        disp_right = self.right_matcher.compute(gray_right, gray_left)
        filtered_disp = self.wls_filter.filter(disp_left, gray_left, None, disp_right)
        
        true_disp = filtered_disp.astype(np.float32) / 16.0
        true_disp[true_disp <= 0.0] = 0.1

        # H x W x 3 matrix (matches image shape)
        points_3D = cv2.reprojectImageTo3D(true_disp, self.Q) / 1000.0

        x = points_3D[:, :, 0]
        y = points_3D[:, :, 1]
        z = points_3D[:, :, 2]

        # === THE FUSION MAGIC ===
        # A point is only valid if it's NOT walkable (mask == 0), and within physical bounds
        valid_condition = (rect_mask == 0) & (y > -0.5) & (y < 0.5) & (z > 0.1) & (z < self.max_distance)

        # Apply the condition to extract only the dangerous obstacle points
        valid_x = x[valid_condition]
        valid_z = z[valid_condition]

        # Convert to 2D Grid Coordinates
        grid_x = np.int32((valid_x + (self.map_width / 2.0)) / self.resolution)
        grid_y = np.int32(valid_z / self.resolution)

        # Filter out points that fall outside the grid array bounds
        in_bounds = (grid_x >= 0) & (grid_x < self.grid_width) & (grid_y >= 0) & (grid_y < self.grid_height)
        grid_x = grid_x[in_bounds]
        grid_y = grid_y[in_bounds]

        # Populate the grid
        occupancy_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
        occupancy_grid[grid_y, grid_x] = 100

        # Thicken the obstacles slightly for safety
        kernel = np.ones((3,3), np.uint8)
        occupancy_grid = cv2.dilate(occupancy_grid, kernel, iterations=1)

        # Publish
        grid_msg = OccupancyGrid()
        grid_msg.header.stamp = left_msg.header.stamp
        grid_msg.header.frame_id = "camera_link"
        
        grid_msg.info.resolution = self.resolution
        grid_msg.info.width = self.grid_width
        grid_msg.info.height = self.grid_height
        grid_msg.info.origin.position.x = -(self.map_width / 2.0)
        grid_msg.info.origin.position.y = 0.0
        grid_msg.info.origin.position.z = 0.0
        
        grid_msg.data = occupancy_grid.astype(np.int8).flatten().tolist()
        
        self.grid_pub.publish(grid_msg)

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