#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from cv_bridge import CvBridge
import cv2
import numpy as np
import acl
import time
import os
import csv
import threading
import subprocess
import re
from collections import deque

class YoloBareMetalNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.declare_parameter('benchmark_mode', False)
        self.benchmark_mode = self.get_parameter('benchmark_mode').get_parameter_value().bool_value
        self.bridge = CvBridge()
        
        self.custom_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=2,
            reliability=ReliabilityPolicy.BEST_EFFORT
        )
        
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

        self.subscription = self.create_subscription(Image, '/camera/camera/color/image_raw', self.image_callback, self.custom_qos)
        self.publisher_ = self.create_publisher(Image, '/inference/yolo_detections', self.custom_qos)
        
        self.CLASS_NAMES = ["vehicle", "pedestrian", "motorcycle", "rider", "pothole", 
                            "curb", "obstacle", "crosswalk", "stair_up", "stair_down"]
        
        self.latencies = deque(maxlen=100)
        self.fps_start = time.time()
        self.fps_count = 0
        self.frame_idx = 0
        self.npu_usage = 0.0
        self.npu_temp = 0.0
        self.metrics_file = "yolo_node_metrics.csv"
        self._init_csv_logger()
        self._start_npu_monitor()
        
        # Force benchmark mode ON to isolate NPU from Python post-processing
        self.benchmark_mode = True
        # Pre-allocate output buffer to stop per-frame np.zeros() & tobytes() GC spikes
        self.raw_output = np.zeros((1, 14, 8400), dtype=np.float32)
        self.output_host_ptr = acl.util.bytes_to_ptr(self.raw_output.tobytes())
        
        self.get_logger().info(f"NPU Benchmark Mode: {self.benchmark_mode}")
        
        self.get_logger().info("🚀 Bare-Metal YOLO Online!")

    def image_callback(self, msg):
        start_time = time.perf_counter()
        cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        orig_h, orig_w = cv_image.shape[:2]
        
        img_data = cv2.dnn.blobFromImage(cv_image, scalefactor=1.0/255.0, size=(640, 640), swapRB=True, crop=False)
        
        bytes_ptr = acl.util.bytes_to_ptr(img_data.tobytes())
        acl.rt.memcpy(self.input_ptr, self.input_size, bytes_ptr, self.input_size, 1)

        # Execute on NPU
        acl.mdl.execute(self.model_id, self.input_dataset, self.output_dataset)

        # Memory Copy: Device -> Host
        acl.rt.memcpy(self.output_host_ptr, self.output_size, self.output_ptr, self.output_size, 2)
        raw_output = self.raw_output  
        
        if self.benchmark_mode:
            # Synchronize to ensure NPU work is complete
            acl.rt.synchronize_stream()
            npu_only_latency = (time.perf_counter() - start_time) * 1000
            
            # Log raw NPU timing
            self.get_logger().info(f"⚡ NPU RAW EXEC: {npu_only_latency:.2f}ms (No CPU post-processing)")
            
            # Publish image with NPU timing overlay
            cv2.putText(cv_image, f"NPU RAW: {npu_only_latency:.1f}ms (Benchmark)", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            out_msg = self.bridge.cv2_to_imgmsg(cv_image, "bgr8")
            out_msg.header = msg.header
            self.publisher_.publish(out_msg)
            
            # Update metrics with NPU-only latency
            self.latencies.append(npu_only_latency)
            self.frame_idx += 1
            self.fps_count += 1
            
            if self.frame_idx % 30 == 0:
                current_time = time.time()
                elapsed = current_time - self.fps_start
                current_fps = self.fps_count / elapsed if elapsed > 0 else 0.0
                avg_lat = sum(self.latencies) / len(self.latencies)
                self.fps_count = 0
                self.fps_start = current_time
                self._log_metrics(avg_lat, current_fps)
            
            return

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
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.latencies.append(latency_ms)
        self.frame_idx += 1
        self.fps_count += 1

        if self.frame_idx % 30 == 0:
            current_time = time.time()
            elapsed = current_time - self.fps_start
            current_fps = self.fps_count / elapsed if elapsed > 0 else 0.0
            avg_lat = sum(self.latencies) / len(self.latencies)
            self.fps_count = 0
            self.fps_start = current_time
            self._log_metrics(avg_lat, current_fps)
            
        cv2.putText(cv_image, f"NPU YOLO: {latency_ms:.1f}ms", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        out_msg = self.bridge.cv2_to_imgmsg(cv_image, "bgr8")
        out_msg.header = msg.header
        self.publisher_.publish(out_msg)
        
    def _init_csv_logger(self):
        with open(self.metrics_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'frame_idx', 'latency_ms', 'avg_latency_ms', 'effective_fps', 'npu_util_pct', 'npu_temp_c'])

    def _log_metrics(self, avg_lat, fps):
        try:
            with open(self.metrics_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.strftime('%Y-%m-%d %H:%M:%S'),
                    self.frame_idx,
                    f"{self.latencies[-1]:.2f}",
                    f"{avg_lat:.2f}",
                    f"{fps:.2f}",
                    f"{self.npu_usage:.1f}",
                    f"{self.npu_temp:.1f}"
                ])
            self.get_logger().info(f"📊 Frame {self.frame_idx} | FPS: {fps:.1f} | Avg Lat: {avg_lat:.1f}ms | NPU: {self.npu_usage}%/{self.npu_temp}°C")
        except Exception as e:
            self.get_logger().warn(f"Metric logging failed: {e}")

    def _monitor_npu(self):
        while hasattr(self, '_npu_monitor_running') and self._npu_monitor_running:
            try:
                res = subprocess.run(['npu-smi', 'info', '-t', 'usages,temperature', '-i', '0'],
                                     capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    lines = res.stdout.strip().split('\n')
                    for line in lines:
                        # Parse table rows: "NPU ID | Utilization | Temperature" or similar
                        parts = [p.strip() for p in line.replace('|', ' ').split()]
                        if len(parts) >= 3 and parts[0].isdigit():
                            # Utilization: strip '%' and convert
                            util_str = parts[1].replace('%', '').replace('Unknown', '0')
                            temp_str = parts[2].replace('°C', '').replace('C', '').replace('Unknown', '0')
                            self.npu_usage = float(util_str) if util_str.isdigit() else 0.0
                            self.npu_temp = float(temp_str) if temp_str.isdigit() else 0.0
                            break
            except Exception:
                pass
            time.sleep(0.5)

    def _start_npu_monitor(self):
        self._npu_monitor_running = True
        self._npu_thread = threading.Thread(target=self._monitor_npu, daemon=True)
        self._npu_thread.start()

    def destroy_node(self):
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
        
        self._npu_monitor_running = False
        if hasattr(self, '_npu_thread'):
            self._npu_thread.join(timeout=1.0)
            
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(YoloBareMetalNode())
    rclpy.shutdown()

if __name__ == '__main__':
    main()