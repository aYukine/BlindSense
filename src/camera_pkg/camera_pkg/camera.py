import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.get_logger().info('Camera node started.')
        try:
            self.cap = cv2.VideoCapture(0)
        except Exception as e:
            self.get_logger().error(f'Failed to initialize camera: {e}')
        self.timer = self.create_timer(0.1, self.capture_frame)
        self.image_publisher = self.create_publisher(Image, 'camera/image_raw', 10)

    def capture_frame(self):
        ret, frame = self.cap.read()
        if ret:
            image = Image()
            image.header.stamp = self.get_clock().now().to_msg()
            image.height = frame.shape[0]
            image.width = frame.shape[1]
            image.encoding = 'bgr8'
            image.data = frame.tobytes()
            self.image_publisher.publish(image)
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