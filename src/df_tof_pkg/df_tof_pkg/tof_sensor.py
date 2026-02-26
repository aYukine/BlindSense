import rclpy
from rclpy.node import Node
from custom_messages.msg import TOF
import serial

class TofPublisher(Node):
    def __init__(self):
        super().__init__('tof_publisher_node')
        self.publisher_ = self.create_publisher(TOF, 'tof_raw_data', 10)
        
        self.declare_parameter('device', '/dev/ttyACM0')
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
                line = self.ser.readline().decode('ascii', errors='ignore').strip()
                
                if ':' in line and line.startswith('y'):
                    header, data_str = line.split(':')
                    row_idx = int(header[1:])
                    row_values = [int(v.strip()) for v in data_str.split(',') if v.strip()]
                    
                    if len(row_values) == 8:
                        start = row_idx * 8
                        self.current_grid[start : start + 8] = row_values

                    if row_idx == 7:
                        msg = TOF()
                        msg.data = self.current_grid
                        self.publisher_.publish(msg)
                        
            except Exception as e:
                self.get_logger().warn(f"Bad packet: {e}")

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