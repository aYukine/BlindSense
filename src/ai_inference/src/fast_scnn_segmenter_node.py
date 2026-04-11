#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np
import time

# ONLY MindSpore gets loaded at the system level
import mindspore_lite as mslite

class FastScnnAscendNode(Node):
    def __init__(self):
        super().__init__('fast_scnn_segmenter')
        
        self.declare_parameter('model_path', 'src/ai_inference/models/converted/fast_scnn_finetune_106.mindir')
        model_file = self.get_parameter('model_path').value
        
        self.get_logger().info(f"Loading MINDIR via MindSpore LITE: {model_file}...")
        
        # --- 1. INITIALIZE HARDWARE FIRST ---
        # Because CV2 doesn't exist yet, there is no Protobuf collision!
        context = mslite.Context()
        context.target = ["ascend"]
        context.ascend.device_id = 0
        
        self.model = mslite.Model()
        self.model.build_from_file(model_file, mslite.ModelType.MINDIR, context)
        self.get_logger().info("Fast-SCNN loaded onto Ascend NPU successfully!")

        # --- 2. LAZY-LOAD OPENCV SECOND ---
        # Now that the NPU is locked in, we safely load the image tools.
        from cv_bridge import CvBridge
        import cv2
        self.cv2 = cv2
        self.bridge = CvBridge()
        
        # Setup ROS communications
        self.subscription = self.create_subscription(Image, 'camera/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Image, 'inference/segmentation_mask', 10)

    def image_callback(self, msg):
        start_time = time.time()
        
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        orig_h, orig_w = frame.shape[:2]
        
        # Preprocess
        img = self.cv2.resize(frame, (1280, 720))
        img = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0 
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        
        # Load Tensor and Run NPU Inference
        inputs = self.model.get_inputs()
        inputs[0].set_data_from_numpy(img)
        outputs = self.model.predict(inputs)
        
        # Postprocess
        out_tensor = outputs[0].get_data_to_numpy()
        class_indices = np.argmax(out_tensor, axis=1)[0]
        
        color_mask = np.zeros((720, 1280, 3), dtype=np.uint8)
        color_mask[class_indices == 1] = [0, 255, 0] # Class 1 (Green)
        color_mask[class_indices == 2] = [0, 0, 255] # Class 2 (Red)
        
        color_mask_resized = self.cv2.resize(color_mask, (orig_w, orig_h), interpolation=self.cv2.INTER_NEAREST)
        blended = self.cv2.addWeighted(frame, 0.7, color_mask_resized, 0.5, 0)
        
        latency_ms = (time.time() - start_time) * 1000
        self.cv2.putText(blended, f"MS-Lite NPU Latency: {latency_ms:.1f}ms", (10, 30), self.cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
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