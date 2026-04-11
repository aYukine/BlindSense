#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import time
import mindspore_lite as mslite

class FastScnnAscendNode(Node):
    def __init__(self):
        super().__init__('fast_scnn_segmenter')
        
        # Point directly to the .mindir file we just exported!
        self.declare_parameter('model_path', 'src/ai_inference/models/converted/fast_scnn_finetune_106.mindir')
        model_file = self.get_parameter('model_path').value
        
        self.subscription = self.create_subscription(Image, 'camera/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Image, 'inference/segmentation_mask', 10)
        self.bridge = CvBridge()
        
        self.get_logger().info(f"Loading Fast-SCNN directly from MINDIR: {model_file}...")
        
        # --- MindSpore Lite Ascend Initialization ---
        context = mslite.Context()
        context.target = ["ascend"]
        context.ascend.device_id = 0
        
        self.model = mslite.Model()
        # Natively load MINDIR
        self.model.build_from_file(model_file, mslite.ModelType.MINDIR, context)
        self.get_logger().info("Fast-SCNN loaded onto Ascend NPU successfully!")

    def image_callback(self, msg):
        start_time = time.time()
        
        # 1. Decode ROS Image
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        orig_h, orig_w = frame.shape[:2]
        
        # 2. Preprocess (Match dummy_input: 1, 3, 720, 1280)
        img = cv2.resize(frame, (1280, 720))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0 
        img = np.transpose(img, (2, 0, 1))    # HWC to CHW
        img = np.expand_dims(img, axis=0)     # Add batch dim
        
        # Convert to MindSpore Lite Tensor
        inputs = self.model.get_inputs()
        inputs[0].set_data_from_numpy(img)
        
        # 3. NPU Inference!
        outputs = self.model.predict(inputs)
        
        # 4. Postprocess
        out_tensor = outputs[0].get_data_to_numpy()
        class_indices = np.argmax(out_tensor, axis=1)[0] # Shape: (720, 1280)
        
        # Map 3 classes to colors (BGR for OpenCV)
        color_mask = np.zeros((720, 1280, 3), dtype=np.uint8)
        color_mask[class_indices == 1] = [0, 255, 0] # Class 1: Green (e.g. Stairs)
        color_mask[class_indices == 2] = [0, 0, 255] # Class 2: Red (e.g. Curb)
        
        # Resize mask back to original video resolution
        color_mask_resized = cv2.resize(color_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        
        # Blend the original frame with the segmentation mask
        blended = cv2.addWeighted(frame, 0.7, color_mask_resized, 0.5, 0)
        
        latency_ms = (time.time() - start_time) * 1000
        cv2.putText(blended, f"Fast-SCNN Latency: {latency_ms:.1f}ms", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # 5. Publish the result
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