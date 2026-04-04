import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import serial
import numpy as np

class TofPublisher(Node):
    def __init__(self):
        super().__init__('tof_publisher_node')
        
        self.image_publisher_ = self.create_publisher(Image, 'tof_depth_image', 10)
        
        self.declare_parameter('device', '/dev/cu.usbmodem1101')
        self.device = self.get_parameter('device').get_parameter_value().string_value
        
        try:
            self.ser = serial.Serial(self.device, 115200, timeout=0.1)
            self.get_logger().info(f"Successfully hooked up to {self.device}")
        except Exception as e:
            self.get_logger().error(f"check the cable: {e}")
            raise e

        self.current_grid = [4000] * 64
        self.create_timer(0.005, self.serial_read_callback)

    def serial_read_callback(self):
        if self.ser.in_waiting > 0:
            try:
                # Read the raw bytes and decode
                raw_bytes = self.ser.readline()
                line = raw_bytes.decode('ascii', errors='ignore').strip()
                
                # Print EVERYTHING that comes over the serial port
                if line:
                    self.get_logger().info(f"RAW SERIAL: {line}")
                        
            except Exception as e:
                self.get_logger().warn(f"Bad packet: {e}")

    def publish_rviz_image(self):
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'tof_link'  
        
        msg.height = 8
        msg.width = 8
        msg.encoding = '16UC1'  
        msg.is_bigendian = 0
        msg.step = 8 * 2       
        
        depth_array = np.array(self.current_grid, dtype=np.uint16)
        msg.data = depth_array.tobytes()
        
        self.image_publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = TofPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()