#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import message_filters
from cv_bridge import CvBridge
import cv2
import time
import os

class UnifiedPresentationExporter(Node):
    def __init__(self):
        super().__init__('presentation_exporter')
        self.bridge = CvBridge()
        
        self.get_logger().info("Initializing Unified AI Fusion Exporter...")

        # 1. Subscribe to BOTH AI output topics
        self.mask_sub = message_filters.Subscriber(self, Image, '/inference/segmentation_mask')
        self.yolo_sub = message_filters.Subscriber(self, Image, '/inference/yolo_detections')
        
        # 2. Synchronize them (Wait for matching timestamps)
        # slop=0.1 means it allows a 100ms difference between the Fast-SCNN and YOLO outputs
        self.ts = message_filters.ApproximateTimeSynchronizer([self.mask_sub, self.yolo_sub], queue_size=10, slop=0.1)
        self.ts.registerCallback(self.sync_callback)

        self.video_writer = None
        
        # Dynamic filename generation to prevent overwriting
        self.output_filename = f"blindense_fused_output_{int(time.time())}.mp4"
        self.get_logger().info(f"Waiting for synchronized AI frames to start recording to {self.output_filename}...")

    def sync_callback(self, mask_msg, yolo_msg):
        # Convert both ROS images to OpenCV frames
        mask_frame = self.bridge.imgmsg_to_cv2(mask_msg, "bgr8")
        yolo_frame = self.bridge.imgmsg_to_cv2(yolo_msg, "bgr8")
        
        # 3. Dynamic Video Writer Initialization
        if self.video_writer is None:
            height, width = yolo_frame.shape[:2]
            # Use dynamic resolution based on incoming frames
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(self.output_filename, fourcc, 30.0, (width, height))
            self.get_logger().info(f"Started recording at {width}x{height}")

        # 4. FUSE THE FRAMES
        # We blend the YOLO image (which has the red boxes) with the Fast-SCNN image (which has the green masks)
        fused_frame = cv2.addWeighted(yolo_frame, 0.6, mask_frame, 0.4, 0)
        
        # Add a unified watermark
        cv2.putText(fused_frame, "HETEROGENEOUS PIPELINE: YOLO + FAST-SCNN", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Write the fused frame to the MP4
        self.video_writer.write(fused_frame)

    def destroy_node(self):
        # Guarantee the video file saves cleanly when Ctrl+C is pressed
        self.get_logger().info("Saving and finalizing video file...")
        if self.video_writer is not None:
            self.video_writer.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = UnifiedPresentationExporter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()