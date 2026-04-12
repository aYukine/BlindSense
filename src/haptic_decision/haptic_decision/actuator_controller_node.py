#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import time

# Attempt to import Orange Pi GPIO library
try:
    import wiringpi
    from wiringpi import GPIO
    WIRINGPI_AVAILABLE = True
except ImportError:
    WIRINGPI_AVAILABLE = False

class HapticActuatorNode(Node):
    def __init__(self):
        super().__init__('haptic_actuator_controller')
        
        # Subscribe to the 3D Mapping/Planner distances [Left, Center, Right] in meters
        self.subscription = self.create_subscription(
            Float32MultiArray,
            '/planner/obstacle_distances',
            self.distance_callback,
            10
        )
        
        # Orange Pi Hardware PWM Pins (Example pins, adjust to your physical wiring)
        self.PIN_LEFT = 2   # wiringOP pin 2
        self.PIN_CENTER = 3 # wiringOP pin 3
        self.PIN_RIGHT = 4  # wiringOP pin 4
        
        if WIRINGPI_AVAILABLE:
            self.get_logger().info("wiringOP detected. Hardware Haptics ONLINE.")
            wiringpi.wiringPiSetup()
            wiringpi.pinMode(self.PIN_LEFT, GPIO.PWM_OUTPUT)
            wiringpi.pinMode(self.PIN_CENTER, GPIO.PWM_OUTPUT)
            wiringpi.pinMode(self.PIN_RIGHT, GPIO.PWM_OUTPUT)
        else:
            self.get_logger().warn("wiringOP missing! Running in Software Simulation Mode.")

    def distance_callback(self, msg):
        # Expecting msg.data = [left_dist, center_dist, right_dist]
        if len(msg.data) < 3:
            return
            
        left_dist, center_dist, right_dist = msg.data
        
        # Convert Distance (Meters) to PWM Vibration Intensity (0-1024)
        # Assuming max range is 3.0 meters. Closer = Stronger vibration.
        pwm_left = self.calculate_pwm(left_dist)
        pwm_center = self.calculate_pwm(center_dist)
        pwm_right = self.calculate_pwm(right_dist)
        
        if WIRINGPI_AVAILABLE:
            wiringpi.pwmWrite(self.PIN_LEFT, pwm_left)
            wiringpi.pwmWrite(self.PIN_CENTER, pwm_center)
            wiringpi.pwmWrite(self.PIN_RIGHT, pwm_right)
            
        self.get_logger().info(f"Haptic Output -> L: {pwm_left/10}% | C: {pwm_center/10}% | R: {pwm_right/10}%")

    def calculate_pwm(self, distance_meters):
        max_dist = 3.0 # Objects beyond 3 meters don't trigger vibration
        safe_dist = 0.5 # Objects closer than 0.5 meters trigger MAXIMUM vibration
        
        if distance_meters >= max_dist:
            return 0
        elif distance_meters <= safe_dist:
            return 1024 # Max PWM
        else:
            # Linear scaling between 0.5m and 3.0m
            intensity = 1.0 - ((distance_meters - safe_dist) / (max_dist - safe_dist))
            return int(intensity * 1024)

def main(args=None):
    rclpy.init(args=args)
    node = HapticActuatorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()