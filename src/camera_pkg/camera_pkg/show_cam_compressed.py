import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import cv2
import numpy as np
from rclpy.qos import QoSProfile, ReliabilityPolicy

class ImageSubscriber(Node):
    def __init__(self):
        super().__init__('image_subscriber_node')
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=1
        )
        self.subscription = self.create_subscription(
            CompressedImage, 
            'camera/image/compressed', 
            self.image_callback, 
            qos_profile
        )

    def image_callback(self, msg):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            cv2.imshow('Pi View', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')


def main(args=None):
    rclpy.init(args=args)
    image_subscriber = ImageSubscriber()
    try:
        rclpy.spin(image_subscriber)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        image_subscriber.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()