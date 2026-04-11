#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import subprocess
import psutil

class MetricLogger(Node):
    def __init__(self):
        super().__init__('metric_logger')
        self.timer = self.create_timer(1.0, self.log_metrics) 
        
    def log_metrics(self):
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        
        # Query Ascend NPU
        try:
            npu_output = subprocess.check_output(['npu-smi', 'info']).decode('utf-8')
            npu_status = "OK" 
        except FileNotFoundError:
            npu_status = "npu-smi not found"
            
        self.get_logger().info(f"Metrics -> CPU: {cpu_usage}% | RAM: {ram_usage}% | NPU: {npu_status}")

def main(args=None):
    rclpy.init(args=args)
    node = MetricLogger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()