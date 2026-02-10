import rclpy
from rclpy.node import Node
from custom_messages.msg import Coordinate, ActionMsg

class AINode(Node):
    def __init__(self):
        super().__init__('ai_node')
        self.get_logger().info('AI node started.')
        self.coor_subscription = self.create_subscription(Coordinate, 'coor_data', self.coordinate_callback, 10)
        self.action_publisher = self.create_publisher(ActionMsg, 'action_data', 10)

    def coordinate_callback(self, msg: Coordinate):
        self.get_logger().info('Received coordinate data in AI node.')
        print(f"AI Node - Latitude: {msg.latitude}, Longitude: {msg.longitude}, Yaw: {msg.yaw}")

        action_msg = ActionMsg()
        action_msg.v_motor1 = 1.0
        action_msg.v_motor2 = 0.47
        self.action_publisher.publish(action_msg)

def main(args=None):
    rclpy.init(args=args)
    ai_node = AINode()
    try:
        rclpy.spin(ai_node)
    except KeyboardInterrupt:
        pass
    finally:
        ai_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()