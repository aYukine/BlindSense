from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='blindsense_ai_pkg',
            executable='ai_node',
            name='ai'
        )
    ])