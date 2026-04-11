#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import time

class FastScnnAscendNode(Node):
    def __init__(self):
        super().__init__('fast_scnn_segmenter')
        self.subscription = self.create_subscription(Image, 'camera/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Image, 'inference/segmentation_mask', 10)
        self.bridge = CvBridge()
        
        self.get_logger().info("Loading Fast-SCNN .om model on Ascend NPU...")
        # --- MindSpore Lite Ascend Init (Placeholder) ---
        # context.ascend.device_id = 0
        # self.model.build_from_file("models/converted/fast_scnn.om", mslite.ModelType.OM, context)

    def image_callback(self, msg):
        start_time = time.time()
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        
        # 1. NPU Inference
        # outputs = self.model.predict(inputs)
        # mask_data = self.postprocess(outputs)
        
        # Placeholder for the colored mask overlay
        mask = np.zeros_like(frame)
        cv2.putText(mask, "Fast-SCNN Active", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Blend the original frame with the segmentation mask
        blended = cv2.addWeighted(frame, 0.7, mask, 0.3, 0)
        
        # 2. Publish the result for 3D fusion and video output
        out_msg = self.bridge.cv2_to_imgmsg(blended, "bgr8")
        self.publisher_.publish(out_msg)

def main(args=None):
    rclpy.init(args=args)
    node = FastScnnAscendNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()