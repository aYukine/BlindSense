import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    bag_play_cmd = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', 'bag/blindsense_perfect_dataset2/blindsense_perfect_dataset2_0.db3'],
        output='screen'
    )

    # 2. Start AI Inference (Assuming the bag publishes images to /camera/image_raw)
    yolo_node = Node(package='ai_inference', executable='yolo_detector_node.py')
    fast_scnn_node = Node(package='ai_inference', executable='fast_scnn_segmenter_node.py')

    # 3. 3D Perception Nodes (Placeholders for where your C++ nodes will go)
    # depth_estimator_node = Node(package='perception_3d', executable='depth_estimator_node')
    # occupancy_grid_node = Node(package='perception_3d', executable='occupancy_grid_node')

    # 4. Haptic Decision Nodes (Placeholders)
    # path_predictor_node = Node(package='haptic_decision', executable='path_predictor_node.py')
    # actuator_controller_node = Node(package='haptic_decision', executable='actuator_controller_node.py')

    # 5. Presentation Exporter
    exporter_node = Node(
        package='visualizer_tools', 
        executable='presentation_exporter',
        parameters=[{'topic_name': 'inference/segmentation_mask'}]
    )

    return LaunchDescription([
        bag_play_cmd,
        yolo_node,
        fast_scnn_node,
        # depth_estimator_node,
        # occupancy_grid_node,
        # path_predictor_node,
        # actuator_controller_node,
        exporter_node
    ])