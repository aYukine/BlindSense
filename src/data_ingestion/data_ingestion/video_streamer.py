import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class VideoStreamer(Node):
    def __init__(self):
        super().__init__('video_streamer')
        self.publisher_ = self.create_publisher(Image, 'camera/image_raw', 10)
        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback) 
        
        video_path = 'video_2026-02-23_08-52-03.mp4' 
        self.cap = cv2.VideoCapture(video_path)
        self.bridge = CvBridge()

        if not self.cap.isOpened():
            self.get_logger().error(f"Could not open video {video_path}")

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.publisher_.publish(msg)
        else:
            self.get_logger().info("Video ended. Looping...")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) 

def main(args=None):
    rclpy.init(args=args)
    node = VideoStreamer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()