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
        for i in range(8):
            action_msg[i] = 1
        
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