import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np

class AINode(Node):
    def __init__(self):
        super().__init__('ai_node')
        self.get_logger().info('AI segmentation node started.')
        
        # Subscribe to the hardware camera feed
        self.img_sub = self.create_subscription(Image, 'camera/left/image_raw', self.image_callback, 10)
        
        # Publish the Fast-SCNN mask (0 = obstacle, 255 = walkable)
        self.mask_pub = self.create_publisher(Image, 'perception/walkable_mask', 10)

    def image_callback(self, msg: Image):
        # 1. Convert incoming image to numpy array for PyTorch/ONNX
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, 3))
        
        # 2. PLACEHOLDER: Run Fast-SCNN Inference here. 
        # For now, we will create a dummy mask indicating the bottom half is "walkable"
        
        mask = np.zeros((msg.height, msg.width), dtype=np.uint8)
        mask[msg.height // 2:, :] = 255  # Fake walkable area
        
        # 3. Publish mask
        mask_msg = Image()
        mask_msg.header.stamp = msg.header.stamp # Keep timestamp for sync
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