import rclpy
from rclpy.node import Node
from custom_messages.msg import ActionMsg

class BlindsenseNode(Node):
    def __init__(self):
        super().__init__('blindsense_node')
        self.get_logger().info('BlindSense main node started.')
        self.action_subscription = self.create_subscription(ActionMsg, 'action_data', self.action_callback, 10)

    def action_callback(self, msg: ActionMsg):
        self.get_logger().info('Received action data in BlindSense node.')
        print(f"BlindSense Node - v_motor1: {msg.v_motor1}, v_motor2: {msg.v_motor2}")


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