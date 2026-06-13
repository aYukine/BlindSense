#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import sys

class MotorTeleopTerminal(Node):
    def __init__(self):
        super().__init__('motor_teleop_terminal')
        # Publisher to match your hardware bridge node
        self.publisher_ = self.create_publisher(String, 'motor', 10)
        self.get_logger().info("Motor Teleop Terminal Node Initialized.")

    def publish_command(self, cmd_string):
        """Helper to package and publish the string command"""
        msg = String()
        msg.data = cmd_string
        self.publisher_.publish(msg)
        print(f">>> Published command: '{cmd_string}' to /motor\n")

def display_menu():
    print("====================================")
    print("       MOTOR CONTROL TERMINAL       ")
    print("====================================")
    print(" [1] FRONT")
    print(" [2] LEFT")
    print(" [3] RIGHT")
    print(" [4] STOP")
    print(" [Q] Quit Application")
    print("------------------------------------")

def main(args=None):
    rclpy.init(args=args)
    node = MotorTeleopTerminal()

    menu_map = {
        '1': 'front',
        '2': 'left',
        '3': 'right',
        '4': 'stop'
    }

    try:
        while rclpy.ok():
            display_menu()
            choice = input("Select an option: ").strip().lower()

            if choice == 'q':
                print("\nShutting down terminal controller...")
                node.publish_command('stop')
                break
            elif choice in menu_map:
                command_to_send = menu_map[choice]
                node.publish_command(command_to_send)
            else:
                print("\n[!] Invalid selection. Please choose 1, 2, 3, 4, or Q.\n")
            
            # FIXED: Changed spin_some to spin_once with a small timeout
            rclpy.spin_once(node, timeout_sec=0.1)

    except KeyboardInterrupt:
        print("\n\nForced exit detected. Issuing emergency stop...")
        node.publish_command('stop')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
