import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import cv2
from rclpy.qos import QoSProfile, ReliabilityPolicy

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=1
        )
        self.get_logger().info('Camera node started.')
        try:
            self.cap = cv2.VideoCapture(0)
        except Exception as e:
            self.get_logger().error(f'Failed to initialize camera: {e}')
        self.timer = self.create_timer(0.1, self.capture_frame)
        self.image_publisher = self.create_publisher(CompressedImage, 'camera/image/compressed', qos_profile)

    def capture_frame(self):
        ret, frame = self.cap.read()
        if ret:
            small_frame = cv2.resize(frame, (640, 480)) 
            msg = CompressedImage()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.format = "jpeg"
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 20]
            success, encoded_image = cv2.imencode('.jpg', small_frame, encode_param)

            if success:
                msg.data = encoded_image.tobytes()
                self.image_publisher.publish(msg)
        else:
            self.get_logger().error('Failed to capture frame.')
    

def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
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