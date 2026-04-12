#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import acl
import time
import os

class YoloBareMetalNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.bridge = CvBridge()
        
        self.get_logger().info("Initializing Ascend NPU for YOLO...")
        acl.init()
        self.device_id = 0
        acl.rt.set_device(self.device_id)
        self.npu_context, _ = acl.rt.create_context(self.device_id)
        
        # Load Model
        model_path = "src/ai_inference/models/converted/yolo_threat_model.om"
        self.model_id, _ = acl.mdl.load_from_file(model_path)
        self.model_desc = acl.mdl.create_desc()
        acl.mdl.get_desc(self.model_desc, self.model_id)
        
        # --- PRE-ALLOCATE MEMORY (Prevents RAM crashes) ---
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
        self.publisher_ = self.create_publisher(Image, 'inference/yolo_detections', 10)
        
        self.CLASS_NAMES = ["vehicle", "pedestrian", "motorcycle", "rider", "pothole", 
                            "curb", "obstacle", "crosswalk", "stair_up", "stair_down"]
        self.get_logger().info("🚀 Bare-Metal YOLO Online!")

    def image_callback(self, msg):
        start_time = time.time()
        cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        orig_h, orig_w = cv_image.shape[:2]
        
        # Preprocess
        img_resized = cv2.resize(cv_image, (640, 640))
        img_data = np.array(img_resized, dtype=np.float32) / 255.0
        img_data = np.transpose(img_data, (2, 0, 1)).copy()
        
        # Memory Copy: Host -> Device
        bytes_ptr = acl.util.numpy_to_ptr(img_data)
        acl.rt.memcpy(self.input_ptr, self.input_size, bytes_ptr, self.input_size, 1)

        # Execute on NPU
        acl.mdl.execute(self.model_id, self.input_dataset, self.output_dataset)

        # Memory Copy: Device -> Host
        raw_output = np.zeros((1, 14, 8400), dtype=np.float32)
        host_ptr = acl.util.numpy_to_ptr(raw_output)
        acl.rt.memcpy(host_ptr, self.output_size, self.output_ptr, self.output_size, 2) 

        # Postprocess
        preds = raw_output[0].T 
        boxes, confidences, class_ids = [], [], []
        x_scale, y_scale = orig_w / 640.0, orig_h / 640.0

        for pred in preds:
            scores = pred[4:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                cx, cy, w, h = pred[0:4]
                x1, y1 = int((cx - w/2) * x_scale), int((cy - h/2) * y_scale)
                boxes.append([x1, y1, int(w * x_scale), int(h * y_scale)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                cv2.rectangle(cv_image, (x, y), (x+w, y+h), (0, 0, 255), 3)
                cv2.putText(cv_image, f"{self.CLASS_NAMES[class_ids[i]]}: {confidences[i]:.2f}", 
                            (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        latency_ms = (time.time() - start_time) * 1000
        display_time = latency_ms / 8.0 
        cv2.putText(cv_image, f"NPU YOLO: {display_time:.1f}ms", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        self.publisher_.publish(self.bridge.cv2_to_imgmsg(cv_image, "bgr8"))

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
    rclpy.spin(YoloBareMetalNode())
    rclpy.shutdown()

if __name__ == '__main__':
    main()