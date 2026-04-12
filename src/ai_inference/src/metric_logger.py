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
        # 1. Get ARM CPU & RAM
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        
        npu_core = "N/A"
        npu_mem = "N/A"
        
        # 2. Query Ascend NPU for real telemetry
        try:
            # Run the command to get NPU usages
            usages_output = subprocess.check_output(['npu-smi', 'info', '-t', 'usages', '-i', '0', '-c', '0']).decode('utf-8')
            
            # Parse the text output to find exactly what we need
            for line in usages_output.split('\n'):
                if "Aicore Usage Rate" in line:
                    npu_core = line.split(':')[1].strip()
                elif "Memory Usage Rate" in line:
                    npu_mem = line.split(':')[1].strip()
                    
            npu_status = f"AI Core: {npu_core}% | NPU Mem: {npu_mem}%" 
            
        except Exception as e:
            npu_status = "npu-smi offline"
            
        # 3. Print the ultimate unified metric log
        self.get_logger().info(f"Metrics -> ARM CPU: {cpu_usage}% | ARM RAM: {ram_usage}% || NPU -> {npu_status}")

def main(args=None):
    rclpy.init(args=args)
    node = MetricLogger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()