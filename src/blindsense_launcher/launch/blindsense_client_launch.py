from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='hw_interface',
            executable='hw_node',
            name='hardware_bridge'
        ),
        Node(
            package='blindsense_pkg',
            executable='blindsense_node',
            name='blindsense'
        ),
        Node (
            package='camera_pkg',
            executable='stereo_depth_node',
            name='depth_map'
        ),
    ])