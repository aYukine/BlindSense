#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import pyrealsense2 as rs
import numpy as np

class BagPlayer(Node):
    def __init__(self):
        super().__init__('bag_player')
        self.publisher_ = self.create_publisher(Image, 'camera/image_raw', 10)
        self.bridge = CvBridge()
        
        self.pipeline = rs.pipeline()
        config = rs.config()
        
        bag_file = 'ITC_1.bag'
        rs.config.enable_device_from_file(config, bag_file)
        
        config.enable_stream(rs.stream.color, rs.format.bgr8, 30)

        try:
            self.profile = self.pipeline.start(config)
            self.get_logger().info(f"Successfully opened {bag_file}")
            
            playback = self.profile.get_device().as_playback()
            playback.set_real_time(True) 
            
            self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)
        except RuntimeError as e:
            self.get_logger().error(f"Failed to open bag file: {e}")

    def timer_callback(self):
        try:
            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()

            if not color_frame:
                return

            color_image = np.asanyarray(color_frame.get_data())

            msg = self.bridge.cv2_to_imgmsg(color_image, "bgr8")
            self.publisher_.publish(msg)
            
        except RuntimeError:
            self.get_logger().info("End of bag file reached.")
            self.timer.cancel() 

def main(args=None):
    rclpy.init(args=args)
    node = BagPlayer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()