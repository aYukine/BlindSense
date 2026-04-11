#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class PresentationExporter(Node):
    def __init__(self):
        super().__init__('presentation_exporter')
        
        self.declare_parameter('topic_name', 'inference/segmentation_mask')
        target_topic = self.get_parameter('topic_name').value
        
        self.subscription = self.create_subscription(Image, target_topic, self.image_callback, 10)
        self.bridge = CvBridge()
        
        # Video Writer Setup
        self.output_filename = 'huawei_edge_ai_demo.mp4'
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Universal MP4 codec
        self.video_writer = None
        
        self.get_logger().info(f"Waiting for frames on {target_topic} to start recording...")

    def image_callback(self, msg):
        # 1. Convert ROS Image to OpenCV format
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        height, width, _ = frame.shape
        
        # 2. Initialize VideoWriter on the first frame (so we know the exact resolution)
        if self.video_writer is None:
            self.video_writer = cv2.VideoWriter(self.output_filename, self.fourcc, 30.0, (width, height))
            self.get_logger().info(f"Started recording {width}x{height} video to {self.output_filename}")

        # 3. Add Presentation Branding (Aligning with Huawei Ecosystem requirement)
        # Dark background strip for text readability
        cv2.rectangle(frame, (0, height - 80), (width, height), (0, 0, 0), -1)
        
        # Branding Text
        cv2.putText(frame, "Hardware: Orange Pi AI Pro (Ascend NPU 20 TOPS)", (15, height - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "Ecosystem: MindSpore & ModelArts", (15, height - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # 4. Write frame to MP4
        self.video_writer.write(frame)

    def destroy_node(self):
        # Ensure the video file saves cleanly when you kill the node (Ctrl+C)
        if self.video_writer is not None:
            self.video_writer.release()
            self.get_logger().info(f"Successfully saved {self.output_filename}")
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = PresentationExporter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass # Allow clean exit on Ctrl+C
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()