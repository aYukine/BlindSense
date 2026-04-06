import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
import cv2
import numpy as np
from cv_bridge import CvBridge
import threading


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.get_logger().info('Stereo Camera hardware node started.')
        self.bridge = CvBridge()
        
        self.left_pub = self.create_publisher(Image, 'camera/left/image_raw', 1)
        self.right_pub = self.create_publisher(Image, 'camera/right/image_raw', 1)
        self.left_info_pub = self.create_publisher(CameraInfo, 'camera/left/camera_info', 1)
        self.right_info_pub = self.create_publisher(CameraInfo, 'camera/right/camera_info', 1)

        xml_path = '/home/rith/Documents/BlindSense/src/camera_pkg/stereoMap.xml' 

        cv_file = cv2.FileStorage(xml_path, cv2.FILE_STORAGE_READ)
        if not cv_file.isOpened():
            self.get_logger().error(f"CRITICAL: Could not open {xml_path}")
            
        self.mapL_x = cv_file.getNode('stereoMapL_x').mat()
        self.mapL_y = cv_file.getNode('stereoMapL_y').mat()
        self.mapR_x = cv_file.getNode('stereoMapR_x').mat()
        self.mapR_y = cv_file.getNode('stereoMapR_y').mat()
        self.projL = cv_file.getNode('projMatrixL').mat()
        self.projR = cv_file.getNode('projMatrixR').mat()
        cv_file.release()
        self.get_logger().info("Calibration maps loaded successfully.")
        
        try:
            gstreamer_pipeline = (
                "v4l2src device=/dev/video2 ! "
                "image/jpeg,width=1280,height=480,framerate=30/1 ! "
                "jpegdec ! videoconvert ! video/x-raw,format=BGR ! "
                "appsink drop=true sync=false max-buffers=1"
            )
            
            self.cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
            
            if not self.cap.isOpened():
                self.get_logger().error("GStreamer pipeline failed to open!")
        except Exception as e:
            self.get_logger().error(f'Failed to initialize camera: {e}')
            
        self.is_running = True
        self.capture_thread = threading.Thread(target=self.capture_loop)
        self.capture_thread.start()
        self.get_logger().info("Dedicated Camera Thread Started.")

    def capture_loop(self):
        while self.is_running and rclpy.ok():
            ret, frame = self.cap.read()
            
            if not ret:
                self.get_logger().warn("Dropped frame!")
                continue 

            stamp = self.get_clock().now().to_msg()

            width = frame.shape[1]
            mid_point = width // 2
            left_frame = np.ascontiguousarray(frame[:, :mid_point])
            right_frame = np.ascontiguousarray(frame[:, mid_point:])

            left_frame = cv2.remap(left_frame, self.mapL_x, self.mapL_y, cv2.INTER_LINEAR)
            right_frame = cv2.remap(right_frame, self.mapR_x, self.mapR_y, cv2.INTER_LINEAR)

            left_msg = self.bridge.cv2_to_imgmsg(left_frame, encoding="bgr8")
            left_msg.header.stamp = stamp
            left_msg.header.frame_id = "camera_left_link"

            right_msg = self.bridge.cv2_to_imgmsg(right_frame, encoding="bgr8")
            right_msg.header.stamp = stamp
            right_msg.header.frame_id = "camera_right_link"

            left_info = self.create_camera_info_msg(stamp, "camera_left_link", left_frame.shape[1], left_frame.shape[0], self.projL)
            right_info = self.create_camera_info_msg(stamp, "camera_right_link", right_frame.shape[1], right_frame.shape[0], self.projR)

            self.left_pub.publish(left_msg)
            self.right_pub.publish(right_msg)
            self.left_info_pub.publish(left_info)
            self.right_info_pub.publish(right_info)
            
    def create_image_msg(self, frame, stamp, frame_id):
        img_msg = Image()
        img_msg.header.stamp = stamp
        img_msg.header.frame_id = frame_id
        img_msg.height = frame.shape[0]
        img_msg.width = frame.shape[1]
        img_msg.encoding = 'bgr8'
        img_msg.step = frame.shape[1] * 3
        img_msg.data = frame.tobytes()
        return img_msg
    
    def create_camera_info_msg(self, stamp, frame_id, width, height, proj_matrix):
        info = CameraInfo()
        info.header.stamp = stamp
        info.header.frame_id = frame_id
        info.width = width
        info.height = height
        
        info.distortion_model = "plumb_bob"
        info.d = [0.0, 0.0, 0.0, 0.0, 0.0] 
        
        info.k = [proj_matrix[0,0], 0.0, proj_matrix[0,2], 
                0.0, proj_matrix[1,1], proj_matrix[1,2], 
                0.0, 0.0, 1.0]
                
        info.p = proj_matrix.flatten().tolist()
    
        return info
    
    def destroy_node(self):
        self.is_running = False
        self.capture_thread.join()
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
    try:
        rclpy.spin(camera_node)
    except KeyboardInterrupt:
        pass
    finally:
        camera_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()