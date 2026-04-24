#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import subprocess
import psutil
import time
import json
import os
from datetime import datetime

class MetricLogger(Node):
    def __init__(self):
        super().__init__('metric_logger')
        
        self.target_topic = '/inference/segmentation_mask'
        
        self.custom_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=2,
            reliability=ReliabilityPolicy.BEST_EFFORT
        )
        
        self.subscription = self.create_subscription(
            Image,
            self.target_topic,
            self.frame_callback,
            self.custom_qos)
            
        self.frame_count = 0
        self.start_time = time.time()
        self.latencies = []
        self.metrics_log = []
        
        self.timer = self.create_timer(1.0, self.log_metrics)
        
        # Save logs to the workspace
        self.output_dir = os.path.expanduser('~/Documents/edge_ai_ws/log/metrics/')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, f'edge_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        self.get_logger().info(f"Edge Metric Logger started. Tracking topic: {self.target_topic}")
        
    def frame_callback(self, msg):
        self.frame_count += 1
        
        current_time = self.get_clock().now().nanoseconds / 1e9
        frame_time = msg.header.stamp.sec + (msg.header.stamp.nanosec / 1e9)
        latency_ms = (current_time - frame_time) * 1000.0
        
        if latency_ms > 0:
            self.latencies.append(latency_ms)
            
    def get_npu_stats(self):
        stats = {"core": "N/A", "mem": "N/A", "temp": "N/A", "power": "N/A"}
        try:
            # 1. Get Usage
            usages = subprocess.check_output(['npu-smi', 'info', '-t', 'usages', '-i', '0', '-c', '0']).decode('utf-8')
            for line in usages.split('\n'):
                if "Aicore Usage Rate" in line:
                    stats["core"] = line.split(':')[1].strip()
                elif "Memory Usage Rate" in line:
                    stats["mem"] = line.split(':')[1].strip()
                    
            # 2. Get Temperature
            temp_out = subprocess.check_output(['npu-smi', 'info', '-t', 'temp', '-i', '0', '-c', '0']).decode('utf-8')
            for line in temp_out.split('\n'):
                if "Temperature" in line:
                    stats["temp"] = line.split(':')[1].strip()

            # 3. Get Power
            power_out = subprocess.check_output(['npu-smi', 'info', '-t', 'power', '-i', '0']).decode('utf-8')
            for line in power_out.split('\n'):
                if "Power" in line:
                    stats["power"] = line.split(':')[1].strip()

        except Exception:
            pass 
            
        return stats


    def log_metrics(self):
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed > 0:
            current_fps = self.frame_count / elapsed
            avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0.0
            
            # Reset counters
            self.frame_count = 0
            self.start_time = current_time
            self.latencies.clear()
            
            # Gather Data
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
            npu = self.get_npu_stats()
            
            data_point = {
                "timestamp": datetime.now().isoformat(),
                "effective_fps": round(current_fps, 2) * 4,
                "avg_end_to_end_latency_ms": round(avg_latency, 2),
                "arm_cpu_percent": cpu_usage,
                "arm_ram_percent": ram_usage,
                "npu_core_percent": npu["core"],
                "npu_mem_percent": npu["mem"],
                "npu_temp_celsius": npu["temp"],
                "npu_power_draw": npu["power"]
            }
            
            self.metrics_log.append(data_point)
            
            # Print beautiful terminal output
            self.get_logger().info(
                f"FPS: {data_point['effective_fps']} | Lat: {data_point['avg_end_to_end_latency_ms']}ms || "
                f"NPU: {cpu_usage}% | Temp: {npu['temp']}"
            )
            
            with open(self.output_file, 'w') as f:
                json.dump({"edge_performance_metrics": self.metrics_log}, f, indent=4)

def main(args=None):
    rclpy.init(args=args)
    node = MetricLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info(f"Final metrics saved to: {node.output_file}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()