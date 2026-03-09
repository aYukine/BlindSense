import rclpy
from rclpy.node import Node
from custom_messages.msg import Coordinate, ActionMsg
import serial

class HardwareBridge(Node):
    def __init__(self):
        super().__init__('hardware_bridge')
        
        self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.05)
        
        self.imu_pub = self.create_publisher(Coordinate, 'imu_data', 10)
        self.motor_sub = self.create_subscription(ActionMsg, 'motor_actions', self.motor_cb, 10)
        
        self.create_timer(0.02, self.update)
        self.get_logger().info("Hardware Bridge Node Initialized")

    def motor_cb(self, msg):
        """Packet format: MOT,v1,v2,v3,v4,v5,v6,v7,v8\n"""
        try:
            # Accessing the array directly from the message
            # msg.motor is a list/tuple of 8 integers (0-255)
            motor_values = msg.motor 
            
            # Join the 8 integers into a CSV string
            # Example result: "MOT,255,128,0,0,0,0,0,0\n"
            payload = "MOT," + ",".join(map(str, motor_values)) + "\n"
            
            self.ser.write(payload.encode('utf-8'))
        except Exception as e:
            self.get_logger().error(f"Serial Write Error: {e}")

    def update(self):
        if self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("IMU,"):
                    # Format: IMU,roll,pitch,yaw
                    _, r, p, y = line.split(',')
                    
                    msg = Coordinate()
                    msg.roll, msg.pitch, msg.yaw = float(r), float(p), float(y)
                    self.imu_pub.publish(msg)
            except ValueError:
                pass

def main(args=None):
    rclpy.init(args=args)
    node = HardwareBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.ser.write("MOT,0,0,0,0,0,0,0,0\n".encode()) # Emergency Stop
    finally:
        node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()