import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class RealActuatorNode(Node):
    def __init__(self):
        super().__init__('actuator_controller')
        
        # Match the Edge BEST_EFFORT QoS
        self.custom_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=2,
            reliability=ReliabilityPolicy.BEST_EFFORT
        )
        
        self.subscription = self.create_subscription(
            Float32MultiArray, 
            '/planner/obstacle_distances', 
            self.distance_callback, 
            self.custom_qos
        )
        
        self.get_logger().info("Hardware Controller Online. Linked to 3D Spatial AI.")

    def distance_callback(self, msg):
        if len(msg.data) >= 3:
            left_dist, center_dist, right_dist = msg.data
            
            # Convert physical distance (meters) to PWM vibration intensity (percentage)
            left_pwm = self.map_distance_to_pwm(left_dist)
            center_pwm = self.map_distance_to_pwm(center_dist)
            right_pwm = self.map_distance_to_pwm(right_dist)
            
            self.get_logger().info(f"Haptic Output -> L: {left_pwm:.1f}% | C: {center_pwm:.1f}% | R: {right_pwm:.1f}%")

    def map_distance_to_pwm(self, distance):
        # Configuration: 3.0 meters = 0% vibration, 0.5 meters = 100% vibration
        max_dist = 3.0
        min_dist = 0.5
        
        if distance >= max_dist:
            return 0.0
        if distance <= min_dist:
            return 100.0
            
        # Linear interpolation
        return 100.0 * (1.0 - ((distance - min_dist) / (max_dist - min_dist)))

def main(args=None):
    rclpy.init(args=args)
    node = RealActuatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()