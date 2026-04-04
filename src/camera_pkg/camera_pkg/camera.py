import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
import numpy as np

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.get_logger().info('Stereo Camera hardware node started.')
        
        self.left_pub = self.create_publisher(Image, 'camera/left/image_raw', 10)
        self.right_pub = self.create_publisher(Image, 'camera/right/image_raw', 10)
        
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        except Exception as e:
            self.get_logger().error(f'Failed to initialize camera: {e}')
            
        # 15 FPS is a good target for stereo + AI processing
        self.timer = self.create_timer(1.0 / 15.0, self.capture_frame)

    def capture_frame(self):
        ret, sbs_frame = self.cap.read()
        if ret:
            # Split the Side-by-Side frame
            half_width = sbs_frame.shape[1] // 2
            left_frame = sbs_frame[:, :half_width]
            right_frame = sbs_frame[:, half_width:]
            
            # Generate ONE timestamp to guarantee synchronization later
            stamp = self.get_clock().now().to_msg()
            
            left_msg = self.create_image_msg(left_frame, stamp, "camera_left_link")
            right_msg = self.create_image_msg(right_frame, stamp, "camera_right_link")
            
            self.left_pub.publish(left_msg)
            self.right_pub.publish(right_msg)
        else:
            self.get_logger().error('Failed to capture frame.')
            
    def create_image_msg(self, frame, stamp, frame_id):
        img_msg = Image()
        img_msg.header.stamp = stamp
        img_msg.header.frame_id = frame_id
        img_msg.height = frame.shape[0]
        img_msg.width = frame.shape[1]
        img_msg.encoding = 'bgr8'
        img_msg.step = frame.shape[1] * 3
        img_msg.data = frame.tobytes()
        return img_msg

def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
    try:
        rclpy.spin(camera_node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(camera_node, 'cap'):
            camera_node.cap.release()
        camera_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()