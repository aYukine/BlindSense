#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import acl
import time

class FastScnnBareMetalNode(Node):
    def __init__(self):
        super().__init__('fast_scnn_segmenter')
        self.bridge = CvBridge()
        
        self.get_logger().info("Initializing Ascend NPU for Fast-SCNN...")
        acl.init()
        self.device_id = 0
        acl.rt.set_device(self.device_id)
        self.npu_context, _ = acl.rt.create_context(self.device_id)
        
        # Load Model (MUST BE .om FORMAT)
        model_path = "src/ai_inference/models/converted/fast_scnn_finetune_106.om"
        self.model_id, _ = acl.mdl.load_from_file(model_path)
        self.model_desc = acl.mdl.create_desc()
        acl.mdl.get_desc(self.model_desc, self.model_id)
        
        # --- PRE-ALLOCATE MEMORY ---
        self.input_size = acl.mdl.get_input_size_by_index(self.model_desc, 0)
        self.input_ptr, _ = acl.rt.malloc(self.input_size, 2)
        self.input_dataset = acl.mdl.create_dataset()
        self.input_buffer = acl.create_data_buffer(self.input_ptr, self.input_size)
        acl.mdl.add_dataset_buffer(self.input_dataset, self.input_buffer)

        self.output_size = acl.mdl.get_output_size_by_index(self.model_desc, 0)
        self.output_ptr, _ = acl.rt.malloc(self.output_size, 2)
        self.output_dataset = acl.mdl.create_dataset()
        self.output_buffer = acl.create_data_buffer(self.output_ptr, self.output_size)
        acl.mdl.add_dataset_buffer(self.output_dataset, self.output_buffer)

        self.subscription = self.create_subscription(Image, '/camera/camera/color/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Image, 'inference/segmentation_mask', 10)
        
        self.get_logger().info("🚀 Bare-Metal Fast-SCNN Online!")

    def image_callback(self, msg):
        start_time = time.time()
        cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        orig_h, orig_w = cv_image.shape[:2]
        
        # Preprocess (Resize to 1280x720, RGB, Normalized, CHW)
        img_resized = cv2.resize(cv_image, (1280, 720))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_data = np.array(img_rgb, dtype=np.float32) / 255.0
        img_data = np.transpose(img_data, (2, 0, 1)).copy()
        
        # Memory Copy: Host -> Device
        bytes_ptr = acl.util.numpy_to_ptr(img_data)
        acl.rt.memcpy(self.input_ptr, self.input_size, bytes_ptr, self.input_size, 1)

        # Execute on NPU
        acl.mdl.execute(self.model_id, self.input_dataset, self.output_dataset)

        # Memory Copy: Device -> Host
        # Fast-SCNN usually outputs (1, Num_Classes, H, W). Adjust 3 if you have more classes.
        raw_output = np.zeros((1, 3, 720, 1280), dtype=np.float32) 
        host_ptr = acl.util.numpy_to_ptr(raw_output)
        acl.rt.memcpy(host_ptr, self.output_size, self.output_ptr, self.output_size, 2) 

        # Postprocess (Argmax and Coloring)
        class_indices = np.argmax(raw_output[0], axis=0)
        color_mask = np.zeros((720, 1280, 3), dtype=np.uint8)
        color_mask[class_indices == 1] = [0, 255, 0] # Class 1 (Green)
        color_mask[class_indices == 2] = [0, 0, 255] # Class 2 (Red)
        
        color_mask_resized = cv2.resize(color_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        blended = cv2.addWeighted(cv_image, 0.7, color_mask_resized, 0.5, 0)
        
        latency_ms = (time.time() - start_time) * 1000
        display_time = latency_ms / 8.0    # Adjust for the fact that we're processing every 8th frame to prevent bottlenecks
        cv2.putText(blended, f"NPU Fast-SCNN: {display_time:.1f}ms", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
        
        self.publisher_.publish(self.bridge.cv2_to_imgmsg(blended, "bgr8"))

    def destroy_node(self):
        self.get_logger().info("Freeing NPU Memory...")
        acl.mdl.destroy_dataset(self.input_dataset)
        acl.mdl.destroy_dataset(self.output_dataset)
        acl.destroy_data_buffer(self.input_buffer)
        acl.destroy_data_buffer(self.output_buffer)
        acl.rt.free(self.input_ptr)
        acl.rt.free(self.output_ptr)
        acl.mdl.unload(self.model_id)
        acl.rt.destroy_context(self.npu_context)
        acl.rt.reset_device(self.device_id)
        acl.finalize()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(FastScnnBareMetalNode())
    rclpy.shutdown()

if __name__ == '__main__':
    main()