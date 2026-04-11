#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import time
import mindspore_lite as mslite

class YoloAscendNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.subscription = self.create_subscription(Image, 'camera/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Image, 'inference/yolo_overlay', 10)
        self.bridge = CvBridge()
        
        self.get_logger().info("Loading YOLO .om model on Ascend NPU...")
        
        context = mslite.Context()
        context.target = ["ascend"]
        context.ascend.device_id = 0
        
        self.model = mslite.Model()
        self.model.build_from_file("src/ai_inference/models/converted/yolo_threat_model.om", mslite.ModelType.OM, context)
        self.get_logger().info("YOLO loaded onto Ascend NPU successfully!")

    def image_callback(self, msg):
        start_time = time.time()
        
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        
        # 1. Standard YOLO Preprocess (640x640)
        img = cv2.resize(frame, (640, 640))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        
        inputs = self.model.get_inputs()
        inputs[0].set_data_from_numpy(img)
        
        # 2. NPU Inference
        outputs = self.model.predict(inputs)
        
        # 3. Calculate metrics
        latency_ms = (time.time() - start_time) * 1000
        cv2.putText(frame, f"YOLO NPU Latency: {latency_ms:.1f}ms", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        out_msg = self.bridge.cv2_to_imgmsg(frame, "bgr8")
        self.publisher_.publish(out_msg)

def main(args=None):
    rclpy.init(args=args)
    node = YoloAscendNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()