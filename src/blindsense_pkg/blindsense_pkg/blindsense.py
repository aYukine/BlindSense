import rclpy
from rclpy.node import Node
from dc_gamepad_msgs.msg import GamePad
from custom_messages.msg import ActionMsg

class BlindsenseNode(Node):
    def __init__(self):
        super().__init__('blindsense_node')
        self.get_logger().info('BlindSense main node started.')
        self.controller_listener = self.create_subscription(GamePad, '/pad', self.gamepad_callback, 10)
        self.action_publisher = self.create_publisher(ActionMsg, '/action', 10)

    def gamepad_callback(self, msg: GamePad):
        action_msg = ActionMsg()
        action_msg.v_motor1 = 0
        action_msg.v_motor2 = 0
        action_msg.v_motor3 = 0
        action_msg.v_motor4 = 0
        action_msg.v_motor5 = 0 
        action_msg.v_motor6 = 0
        action_msg.v_motor7 = 0
        action_msg.v_motor8 = 0
        
        self.action_publisher.publish(action_msg)

def main(args=None):
    rclpy.init(args=args)
    blindsense_node = BlindsenseNode()
    try:
        rclpy.spin(blindsense_node)
    except KeyboardInterrupt:
        pass
    finally:
        blindsense_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()