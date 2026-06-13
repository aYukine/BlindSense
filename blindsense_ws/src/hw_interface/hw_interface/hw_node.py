import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
from std_msgs.msg import String
import serial
import math
import time

class HardwareBridge(Node):
    def __init__(self):
        super().__init__('imu_hardware_bridge')
        
        # --- CONFIGURATION ---
        SERIAL_PORT = "/dev/ttyUSB0"
        BAUD_RATE = 115200
        
        self.ACCEL_SCALE = 16384.0  
        self.GYRO_SCALE = 131.0     

        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01) # Low timeout for crisp control
        except Exception as e:
            self.get_logger().error(f"Failed to open serial port {SERIAL_PORT}: {e}")
            raise e

        # --- ROS 2 RELEASES (PUBLISHERS & SUBSCRIBERS) ---
        self.imu_pub = self.create_publisher(Vector3, 'imu_data', 10)
        
        # Listening to the /motor topic using standard String messages
        self.motor_sub = self.create_subscription(
            String,
            'motor',
            self.motor_callback,
            10
        )
        
        # --- IMU VARIABLES ---
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.last_time = time.time()
        
        self.gyro_z_offset = 0.0
        self.calibration_samples = 100
        self.samples_read = 0
        self.calibrating = True
        self.gyro_data_buffer = []

        self.get_logger().info("==============================================================")
        self.get_logger().info("CALIBRATION: Place the sensor flat and PERFECTLY STILL...")
        self.get_logger().info("==============================================================")

        # High frequency loop to handle incoming IMU lines quickly
        self.create_timer(0.01, self.read_imu_update)

    def motor_callback(self, msg):
        """Processes high-level directional strings and sends direct pin-states to ESP32"""
        command = msg.data.lower().strip()
        
        if command == "front":
            # Both wheels forward
            self.send_serial_cmd("L_HIGH")
            self.send_serial_cmd("R_HIGH")
        elif command == "right":
            # Turn right: Left wheel forward, Right wheel static/backwards
            self.send_serial_cmd("L_HIGH")
            self.send_serial_cmd("R_LOW")
        elif command == "left":
            # Turn left: Left wheel static/backwards, Right wheel forward
            self.send_serial_cmd("L_LOW")
            self.send_serial_cmd("R_HIGH")
        elif command == "stop":
            self.send_serial_cmd("STOP")
        else:
            self.get_logger().warn(f"Unknown movement command received: {command}")

    def send_serial_cmd(self, cmd_string):
        """Helper to safely pass instructions down the physical line"""
        try:
            packet = f"{cmd_string}\n".encode('utf-8')
            self.ser.write(packet)
        except Exception as e:
            self.get_logger().error(f"Serial write error: {e}")

    def read_imu_update(self):
        """Checks serial lines for incoming MPU6050 packets and broadcasts transformations"""
        if self.ser.in_waiting <= 0:
            return

        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line or "Accel:" not in line:
                return
                
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            parts = line.split('|')
            accel_parts = parts[0].replace("Accel: ", "").split()
            gyro_parts = parts[1].replace("Gyro: ", "").split()
            
            ax_raw = float(accel_parts[0].split('=')[1])
            ay_raw = float(accel_parts[1].split('=')[1])
            az_raw = float(accel_parts[2].split('=')[1])
            gz_raw = float(gyro_parts[2].split('=')[1]) 

            if self.calibrating:
                self.gyro_data_buffer.append(gz_raw)
                self.samples_read += 1
                if self.samples_read >= self.calibration_samples:
                    self.gyro_z_offset = sum(self.gyro_data_buffer) / len(self.gyro_data_buffer)
                    self.calibrating = False
                    self.get_logger().info(">>> Calibration Complete! Node is fully operational. <<<")
                return

            ax = ax_raw / self.ACCEL_SCALE
            ay = ay_raw / self.ACCEL_SCALE
            az = az_raw / self.ACCEL_SCALE
            
            self.roll = math.atan2(ay, az)
            self.pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))
            
            corrected_gz = gz_raw - self.gyro_z_offset
            gz_deg_per_sec = corrected_gz / self.GYRO_SCALE
            
            if abs(gz_deg_per_sec) > 0.2: 
                self.yaw += math.radians(gz_deg_per_sec) * dt

            msg = Vector3()
            msg.x = self.roll   
            msg.y = self.pitch  
            msg.z = self.yaw    
            
            self.imu_pub.publish(msg)

        except (ValueError, IndexError):
            pass
        except Exception as e:
            self.get_logger().error(f"Unexpected processing error: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = HardwareBridge()
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