import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO
from rclpy.qos import qos_profile_sensor_data

class YoloThreatNode(Node):
    def __init__(self):
        super().__init__('yolo_threat_node')
        
        self.bridge = CvBridge()

        pkg_dir = get_package_share_directory('ai_perception_pkg')
        model_path = os.path.join(pkg_dir, 'models', 'best.pt')
        
        self.get_logger().info(f"Loading YOLO-NAS/YOLOv8 from: {model_path}")
        self.model = YOLO(model_path)
        
        self.subscription = self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.image_callback,
            qos_profile_sensor_data 
        )
        
        self.debug_publisher = self.create_publisher(Image, '/ai/yolo_debug_image', 10)
        self.get_logger().info("YOLO Threat Detector is ONLINE and waiting for images...")

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
            results = self.model(cv_image, stream=True, verbose=False)
            
            for r in results:
                annotated_frame = r.plot() 
                
                debug_msg = self.bridge.cv2_to_imgmsg(annotated_frame, "bgr8")
                debug_msg.header = msg.header # Keep the exact same timestamp!
                self.debug_publisher.publish(debug_msg)
                
        except Exception as e:
            self.get_logger().error(f"Failed to process image: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = YoloThreatNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()