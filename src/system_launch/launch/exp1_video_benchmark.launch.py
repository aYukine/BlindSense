import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition

def generate_launch_description():
    # --- 1. SAFETY SWITCHES & ARGUMENTS ---
    run_streamer_arg = DeclareLaunchArgument('run_streamer', default_value='false', description='WARNING: Set true ONLY for live camera, NOT for datasets')
    record_mp4_arg = DeclareLaunchArgument('record_mp4', default_value='true', description='Record the fused presentation video')

    run_streamer = LaunchConfiguration('run_streamer')
    record_mp4 = LaunchConfiguration('record_mp4')

    # --- 2. DATA INGESTION ---
    # Locked behind the safety switch so it never hijacks your .db3 bag runs again
    video_streamer_node = Node(
        package='data_ingestion',
        executable='video_streamer',
        name='video_streamer',
        condition=IfCondition(run_streamer),
        output='screen'
    )

    # --- 3. BARE-METAL AI NPU NODES ---
    yolo_node = Node(
        package='ai_inference',
        executable='yolo_detector_node.py', 
        name='yolo_detector',
        output='screen'
    )

    fast_scnn_node = Node(
        package='ai_inference',
        executable='fast_scnn_segmenter_node.py',
        name='fast_scnn_segmenter',
        output='screen'
    )

    # --- 4. 3D PERCEPTION (C++ ENGINES) ---
    depth_estimator_node = Node(
        package='perception_3d',
        executable='depth_estimator_node',
        name='depth_estimator',
        output='screen'
    )

    spatial_fusion_node = Node(
        package='perception_3d',
        executable='spatial_fusion_node',
        name='spatial_fusion',
        output='screen'
    )

    # --- 5. HAPTIC DECISION & HARDWARE ---
    actuator_controller_node = Node(
        package='haptic_decision',
        executable='actuator_controller_node.py',
        name='actuator_controller',
        output='screen'
    )

    # --- 6. TELEMETRY & PRESENTATION ---
    metric_logger_node = Node(
        package='ai_inference',
        executable='metric_logger.py',
        name='metric_logger',
        output='screen'
    )

    presentation_exporter_node = Node(
        package='visualizer_tools',
        executable='presentation_exporter.py', # The new Unified script
        name='presentation_exporter',
        condition=IfCondition(record_mp4),
        output='screen'
    )

    return LaunchDescription([
        run_streamer_arg,
        record_mp4_arg,
        video_streamer_node,
        # yolo_node,
        fast_scnn_node,
        depth_estimator_node,
        spatial_fusion_node,
        actuator_controller_node,
        metric_logger_node,
        presentation_exporter_node
    ])