from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='sensor_pkg',
            executable='sensor_node',
            name='sensor'
        ),
        Node(
            package='blindsense_pkg',
            executable='blindsense_node',
            name='blindsense'
        )
    ])