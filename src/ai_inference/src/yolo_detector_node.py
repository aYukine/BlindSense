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
        
        resized = cv2.resize(cv_image, (640, 640), interpolation=cv2.INTER_LINEAR)
        img_data = (resized[:, :, ::-1].astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis, ...] 
        
        bytes_ptr = acl.util.bytes_to_ptr(img_data.tobytes())
        acl.rt.memcpy(self.input_ptr, self.input_size, bytes_ptr, self.input_size, 1)

        # Execute on NPU
        acl.mdl.execute(self.model_id, self.input_dataset, self.output_dataset)

        # Memory Copy: Device -> Host
        acl.rt.memcpy(self.output_host_ptr, self.output_size, self.output_ptr, self.output_size, 2)
        raw_output = self.raw_output  
        
        if self.benchmark_mode:
            # Synchronize to ensure NPU work is complete
            # acl.rt.synchronize_stream()
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
        preds = raw_output[0].T  # Shape: (8400, 14)
        x_scale, y_scale = orig_w / 640.0, orig_h / 640.0

        # Extract scores for all classes at once (vectorized)
        scores = preds[:, 4:]  # (8400, 10)
        class_ids = np.argmax(scores, axis=1)  # (8400,)
        confidences = np.max(scores, axis=1)   # (8400,)

        # Filter by confidence threshold (vectorized boolean indexing)
        mask = confidences > 0.5
        filtered_preds = preds[mask]
        filtered_conf = confidences[mask]
        filtered_cls = class_ids[mask]

        if len(filtered_preds) > 0:
            # Decode boxes: [cx, cy, w, h] -> [x1, y1, x2, y2]
            boxes_xywh = filtered_preds[:, :4]  # (N, 4)
            boxes_xyxy = np.zeros_like(boxes_xywh)
            boxes_xyxy[:, 0] = (boxes_xywh[:, 0] - boxes_xywh[:, 2]/2) * x_scale  # x1
            boxes_xyxy[:, 1] = (boxes_xywh[:, 1] - boxes_xywh[:, 3]/2) * y_scale  # y1
            boxes_xyxy[:, 2] = boxes_xywh[:, 2] * x_scale  # width
            boxes_xyxy[:, 3] = boxes_xywh[:, 3] * y_scale  # height
            
            # Convert to list format for NMS (cv2 requires list of lists)
            boxes_list = boxes_xyxy.astype(int).tolist()
            conf_list = filtered_conf.tolist()
            
            # Run NMS (still requires cv2, but only on filtered boxes)
            indices = cv2.dnn.NMSBoxes(boxes_list, conf_list, 0.5, 0.4)
            
            if len(indices) > 0:
                for i in indices.flatten():
                    idx = int(i)
                    x1, y1, x2, y2 = boxes_xyxy[idx].astype(int)
                    w, h = x2 - x1, y2 - y1
                    cv2.rectangle(cv_image, (x1, y1), (x1+w, y1+h), (0, 0, 255), 3)
                    cv2.putText(cv_image, f"{self.CLASS_NAMES[filtered_cls[idx]]}: {filtered_conf[idx]:.2f}",
                               (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
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
                # Fetch Utilization (separate command per Orange Pi npu-smi spec)
                res_u = subprocess.run(['npu-smi', 'info', '-t', 'usages', '-i', '0'], 
                                       capture_output=True, text=True, timeout=2)
                if res_u.returncode == 0:
                    for line in res_u.stdout.split('\n'):
                        if 'Aicore Usage Rate' in line and ':' in line:
                            parts = line.split(':')
                            if len(parts) >= 2:
                                val = parts[1].strip()
                                if val and (val.replace('.','').isdigit() or val[0].isdigit()):
                                    self.npu_usage = float(val)
                                break
                # Fetch Temperature (separate command)
                res_t = subprocess.run(['npu-smi', 'info', '-t', 'temp', '-i', '0'], 
                                       capture_output=True, text=True, timeout=2)
                if res_t.returncode == 0:
                    for line in res_t.stdout.split('\n'):
                        if 'Temperature (C)' in line and ':' in line:
                            parts = line.split(':')
                            if len(parts) >= 2:
                                val = parts[1].strip()
                                if val and (val.replace('.','').isdigit() or val[0].isdigit()):
                                    self.npu_temp = float(val)
                                break
            except Exception:
                pass  # Silent fail to avoid blocking inference thread
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