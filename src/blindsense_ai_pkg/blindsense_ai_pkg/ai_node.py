import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np

class AINode(Node):
    def __init__(self):
        super().__init__('ai_node')
        self.get_logger().info('AI segmentation node started.')
        
        self.img_sub = self.create_subscription(Image, 'camera/left/image_raw', self.image_callback, 10)
        
        self.mask_pub = self.create_publisher(Image, 'perception/walkable_mask', 10)

    def image_callback(self, msg: Image):
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, 3))
        
        mask = np.zeros((msg.height, msg.width), dtype=np.uint8)
        mask[msg.height // 2:, :] = 255  
        
        # 3. Publish mask
        mask_msg = Image()
        mask_msg.header.stamp = msg.header.stamp 
        mask_msg.header.frame_id = msg.header.frame_id
        mask_msg.height = msg.height
        mask_msg.width = msg.width
        mask_msg.encoding = 'mono8'
        mask_msg.step = msg.width
        mask_msg.data = mask.tobytes()
        
        self.mask_pub.publish(mask_msg)

def main(args=None):
    rclpy.init(args=args)
    ai_node = AINode()
    try:
        rclpy.spin(ai_node)
    except KeyboardInterrupt:
        pass
    finally:
        ai_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()