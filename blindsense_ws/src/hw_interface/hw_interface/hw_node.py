import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
import serial
import math
import time

class HardwareBridge(Node):
    def __init__(self):
        super().__init__('imu_hardware_bridge')
        
        # --- CONFIGURATION ---
        SERIAL_PORT = "/dev/ttyUSB0"
        BAUD_RATE = 115200
        
        # MPU-6050 Scale Factors
        self.ACCEL_SCALE = 16384.0  # LSB Sensitivity for +/- 2g range
        self.GYRO_SCALE = 131.0     # LSB Sensitivity for +/- 250 deg/s range

        # Initialize Serial Connection
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)
        except Exception as e:
            self.get_logger().error(f"Failed to open serial port {SERIAL_PORT}: {e}")
            raise e

        # Standard ROS 2 Publisher (Vector3 provides x, y, z fields which map to roll, pitch, yaw)
        self.imu_pub = self.create_publisher(Vector3, 'imu_data', 10)
        
        # --- MOTION TRACKING & CALIBRATION VARIABLES ---
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

        # High-frequency processing timer (~50Hz matching the 0.02s interval)
        self.create_timer(0.02, self.update)

    def update(self):
        if self.ser.in_waiting <= 0:
            return

        try:
            # Read and parse incoming line
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line or "Accel:" not in line:
                return
                
            # Delta time tracking for real-world integration physics
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            # Parse text data stream
            # Format: Accel: X=123 Y=456 Z=789 | Gyro: X=12 Y=34 Z=56
            parts = line.split('|')
            accel_parts = parts[0].replace("Accel: ", "").split()
            gyro_parts = parts[1].replace("Gyro: ", "").split()
            
            ax_raw = float(accel_parts[0].split('=')[1])
            ay_raw = float(accel_parts[1].split('=')[1])
            az_raw = float(accel_parts[2].split('=')[1])
            gz_raw = float(gyro_parts[2].split('=')[1]) 

            # --- PHASE 1: BOOTSTRAP BIAS CALIBRATION ---
            if self.calibrating:
                self.gyro_data_buffer.append(gz_raw)
                self.samples_read += 1
                if self.samples_read >= self.calibration_samples:
                    self.gyro_z_offset = sum(self.gyro_data_buffer) / len(self.gyro_data_buffer)
                    self.calibrating = False
                    self.get_logger().info(">>> Calibration Complete! Streaming standard telemetry. <<<")
                return

            # --- PHASE 2: PHYSICS MATH INTEGRATION ---
            # Standard G-Force normalization
            ax = ax_raw / self.ACCEL_SCALE
            ay = ay_raw / self.ACCEL_SCALE
            az = az_raw / self.ACCEL_SCALE
            
            # True 1:1 Orientation trigonometry
            self.roll = math.atan2(ay, az)
            self.pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))
            
            # Filter and integrate Yaw rotation velocity
            corrected_gz = gz_raw - self.gyro_z_offset
            gz_deg_per_sec = corrected_gz / self.GYRO_SCALE
            
            if abs(gz_deg_per_sec) > 0.2: 
                self.yaw += math.radians(gz_deg_per_sec) * dt

            # --- PHASE 3: ROS 2 STANDARD MESSAGE PUBLISH ---
            msg = Vector3()
            msg.x = self.roll   # Standard ROS mapping: X axis handles Roll
            msg.y = self.pitch  # Standard ROS mapping: Y axis handles Pitch
            msg.z = self.yaw    # Standard ROS mapping: Z axis handles Yaw
            
            self.imu_pub.publish(msg)

        except (ValueError, IndexError) as e:
            # Drop malformed packets silently without stopping node threads
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
