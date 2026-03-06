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
            package='blindsense_ai_pkg',
            executable='ai_node',
            name='ai'
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
        # Node(
        #     package='tf2_ros',
        #     executable='static_transform_publisher',
        #     arguments=['0', '0', '0', '0', '0', '0', 'map', 'camera_link']
        # )
    ])