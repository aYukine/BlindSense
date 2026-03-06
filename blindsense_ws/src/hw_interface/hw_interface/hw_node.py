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
            # We round to 2 decimals to save bandwidth on the serial line
            v = [msg.v_motor1, msg.v_motor2, msg.v_motor3, msg.v_motor4, 
                 msg.v_motor5, msg.v_motor6, msg.v_motor7, msg.v_motor8]
            
            payload = "MOT," + ",".join([f"{val:.2f}" for val in v]) + "\n"
            self.ser.write(payload.encode('utf-8'))
        except Exception as e:
            self.get_logger().error(f"Write Error: {e}")

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