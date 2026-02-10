import rclpy
from rclpy.node import Node
from custom_messages.msg import Coordinate

class SensorNode(Node):
    def __init__(self):
        super().__init__('sensor_node')
        self.get_logger().info('Sensor node has been started.')
        self.timer = self.create_timer(1.0, self.read_sensor_data)
        self.coor_publisher = self.create_publisher(Coordinate, 'coor_data', 10)

    def read_sensor_data(self):
        sensor_data = Coordinate()
        sensor_data.latitude = 37.7749
        sensor_data.longitude = -122.4194
        sensor_data.yaw = 0.0
        self.coor_publisher.publish(sensor_data)

def main(args=None):
    rclpy.init(args=args)
    sensor_node = SensorNode()
    try:
        rclpy.spin(sensor_node)
    except KeyboardInterrupt:
        pass
    finally:
        sensor_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()