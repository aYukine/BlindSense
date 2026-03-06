import rclpy
from rclpy.node import Node
from dc_gamepad_msgs.msg import GamePad
import socket

class GamePadNode(Node):
    def __init__(self):
        Node.__init__(self, 'gamepad_node')    
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = s.getsockname()[0]
        s.close()
        self.datapub = self.create_publisher(GamePad, '/pad', 10)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = 12349
        self.sock.bind((self.ip, self.port))
        self.previous_button = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.get_logger().info(f"Gamepad node started on address: {self.ip}:{self.port}")
        while True:
            self.listen_data()

    def listen_data(self):
        msg = GamePad()

        msg.previous_button_up = bool(self.previous_button[0])
        msg.previous_button_left = bool(self.previous_button[1])
        msg.previous_button_right = bool(self.previous_button[2])
        msg.previous_button_down = bool(self.previous_button[3])
        msg.previous_button_y = bool(self.previous_button[4])
        msg.previous_button_x = bool(self.previous_button[5])
        msg.previous_button_b = bool(self.previous_button[6])
        msg.previous_button_a = bool(self.previous_button[7])
        
        msg.previous_button_lt = bool(self.previous_button[8])
        msg.previous_button_lb = bool(self.previous_button[9])
        msg.previous_button_rt = bool(self.previous_button[10])
        msg.previous_button_rb = bool(self.previous_button[11])
        msg.previous_button_m1 = bool(self.previous_button[12])
        msg.previous_button_m2 = bool(self.previous_button[13])

        data = self.sock.recv(8)
        msg.left_analog_x = data[0]
        msg.left_analog_y = data[1]
        msg.right_analog_x = data[2]
        msg.right_analog_y = data[3]
        msg.axis_x = data[6]
        msg.axis_y = data[7]
        msg.dpad_up = bool(data[4] & 1)
        msg.dpad_left = bool(data[4] & 2)
        msg.dpad_right = bool(data[4] & 4)
        msg.dpad_down = bool(data[4] & 8)
        msg.button_y = bool(data[4] & 16)
        msg.button_x = bool(data[4] & 32)
        msg.button_b = bool(data[4] & 64)
        msg.button_a = bool(data[4] & 128)

        msg.button_lt = bool(data[5] & 1)
        msg.button_lb = bool(data[5] & 2)
        msg.button_rt = bool(data[5] & 4)
        msg.button_rb = bool(data[5] & 8)
        msg.button_m1 = bool(data[5] & 16)
        msg.button_m2 = bool(data[5] & 32)

        self.datapub.publish(msg)
        self.previous_button = [msg.dpad_up, msg.dpad_left, msg.dpad_right, msg.dpad_down, msg.button_y, msg.button_x, msg.button_b, msg.button_a, msg.button_lt, msg.button_lb, msg.button_rt, msg.button_rb, msg.button_m1, msg.button_m2, msg.axis_x, msg.axis_y]
    
    def shutdown(self):
        self.sock.close()
        self.datapub.destroy()
        self.get_logger().info(f"Gamepad node stopped on address: {self.ip}:{self.port}, shutting down...")

def main(args=None):
    rclpy.init(args=args)
    gamepad_node = GamePadNode()

    try:
        rclpy.spin(gamepad_node)
    except KeyboardInterrupt:
        pass
    finally:
        gamepad_node.shutdown()
        rclpy.shutdown()


if __name__=="__main__":
    main()
