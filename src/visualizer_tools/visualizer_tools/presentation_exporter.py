import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
import message_filters

class PresentationExporter(Node):
    def __init__(self):
        super().__init__('presentation_exporter')
        self.bridge = CvBridge()
        
        # Synchronize YOLO and Mask images
        self.mask_sub = message_filters.Subscriber(self, Image, '/inference/segmentation_mask')
        self.yolo_sub = message_filters.Subscriber(self, Image, '/inference/yolo_detections')
        self.ts = message_filters.ApproximateTimeSynchronizer([self.mask_sub, self.yolo_sub], 10, 0.5)
        self.ts.registerCallback(self.fusion_callback)
        
        # Video Writer Settings
        self.out = None
        self.get_logger().info("Waiting for synchronized AI frames...")

    def fusion_callback(self, mask_msg, yolo_msg):
        mask_img = self.bridge.imgmsg_to_cv2(mask_msg, "bgr8")
        yolo_img = self.bridge.imgmsg_to_cv2(yolo_msg, "bgr8")
        
        # Fuse the two AI outputs
        fused_img = cv2.addWeighted(yolo_img, 0.7, mask_img, 0.3, 0)
        
        # Initialize video writer on first frame
        if self.out is None:
            h, w, _ = fused_img.shape
            self.out = cv2.VideoWriter(f'ITC1_processed_results.mp4', 
                                     cv2.VideoWriter_fourcc(*'mp4v'), 30, (w, h))
        
        self.out.write(fused_img)

def main(args=None):
    rclpy.init(args=args)
    node = PresentationExporter()
    rclpy.spin(node)
    if node.out: node.out.release()
    rclpy.shutdown()