#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import random

class HapticControllerNode(Node):
    def __init__(self):
        super().__init__('actuator_controller_node')
        
        self.declare_parameter('user_mode', 'beginner')
        self.timer = self.create_timer(2.0, self.simulate_environment_perception)
        
        self.get_logger().info("Corrected Dual-Tactile Language System Initialized.")
        self.get_logger().info(f"Current Mode: {self.get_parameter('user_mode').value.upper()}")

    def calculate_haptic_feedback(self, angle_deg, distance_meters, mode):
        pressure_intensity = max(0, min(100, int((3.0 - distance_meters) / 2.5 * 100)))

        # 2. Vibration Logic (Pattern = Direction to move)
        if angle_deg < -15:
            # Object is on the left, tell user to turn right
            vibration_pattern = "Buzz Right Side (Turn Right)"
        elif angle_deg > 15:
            vibration_pattern = "Buzz Left Side (Turn Left)"
        else:
            vibration_pattern = "Double Pulse Both Sides (Stop/Turn Around)"

        if mode == 'advanced':
            if distance_meters > 1.5:
                return "SUPPRESSED (Advanced Mode - Object is far enough away)"
            vibration_pattern += " [Short burst]" 

        return f"PWM_VIB: {vibration_pattern} | PWM_PRESS: {pressure_intensity}%"

    def simulate_environment_perception(self):
        """Simulates path planning data for performance testing"""
        mode = self.get_parameter('user_mode').value
        
        angle = round(random.uniform(-45.0, 45.0), 1)
        distance = round(random.uniform(0.5, 3.0), 2)
        
        self.get_logger().info(f"--- Threat Detected: {distance}m away at {angle} degrees ---")
        
        haptic_command = self.calculate_haptic_feedback(angle, distance, mode)
        
        if "SUPPRESSED" in haptic_command:
            self.get_logger().info(f"Haptic Output: {haptic_command}\n")
        else:
            self.get_logger().info(f"\033[1;32mHaptic Output: -> {haptic_command}\033[0m\n")


def main(args=None):
    rclpy.init(args=args)
    node = HapticControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()