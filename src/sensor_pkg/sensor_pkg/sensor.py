import rclpy
from rclpy.node import Node
from custom_messages.msg import Coordinate
import serial

class SensorNode(Node):
    def __init__(self):
        super().__init__('sensor_bridge_node')
        self.coor_publisher = self.create_publisher(Coordinate, 'coor_data', 10)
        
        self.serial_port = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        
        self.get_logger().info('Serial Bridge Started. Listening to ESP32...')
        self.timer = self.create_timer(0.05, self.read_serial_data)

    def read_serial_data(self):
        if self.serial_port.in_waiting > 0:
            try:
                line = self.serial_port.readline().decode('utf-8').strip()
                data = line.split(',')
                print(data)
                
                if len(data) == 3:
                    msg = Coordinate()
                    msg.latitude = 37.7749
                    msg.longitude = -122.4194
                    msg.altitude = 0.0
                    
                    # Parsed Orientation
                    msg.roll = float(data[0])
                    msg.pitch = float(data[1])
                    msg.yaw = float(data[2])
                    
                    self.coor_publisher.publish(msg)
                    
            except Exception as e:
                self.get_logger().error(f'Serial Error: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = SensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.serial_port.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()