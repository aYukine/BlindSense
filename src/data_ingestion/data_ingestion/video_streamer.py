import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import sys, os, cv2, numpy as np

# Force path to acllite
sys.path.append(os.path.join(os.path.dirname(__file__), 'acllite'))
from videocapture import VideoCapture
from acllite_resource import AclLiteResource

class VideoStreamer(Node):
    def __init__(self):
        super().__init__('video_streamer')
        self.pub = self.create_publisher(Image, '/camera/camera/color/image_raw', 10)
        self.bridge = CvBridge()
        self.res = AclLiteResource(); self.res.init()
        
        # Point to the raw bitstream you created with ffmpeg
        v_path = "/home/HwHiAiUser/Documents/edge_ai_ws/data/ITC1_scnn.h264"
        self.cap = VideoCapture(v_path)
        self.create_timer(0.04, self.timer_cb)
        self.get_logger().info("🚀 STREAMER ACTIVE")

    def timer_cb(self):
        ret, frame = self.cap.read()
        if ret and frame is not None:
            # Convert NPU memory to CPU-friendly BGR
            img = frame.byte_data_to_npvec() if hasattr(frame, 'byte_data_to_npvec') else frame
            if img.shape[0] > 720: # Handle NV12
                img = cv2.cvtColor(img, cv2.COLOR_YUV2BGR_NV12)
            self.pub.publish(self.bridge.cv2_to_imgmsg(img, "bgr8"))
        else:
            self.cap.restart()

def main():
    rclpy.init(); node = VideoStreamer()
    try: rclpy.spin(node)
    except: pass
    finally: node.res.destroy(); rclpy.shutdown()