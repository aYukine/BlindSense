import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition

def generate_launch_description():
    run_yolo_arg = DeclareLaunchArgument('run_yolo', default_value='true', description='Run YOLO node')
    run_fast_scnn_arg = DeclareLaunchArgument('run_fast_scnn', default_value='true', description='Run Fast-SCNN node')
    record_mp4_arg = DeclareLaunchArgument('record_mp4', default_value='true', description='Record output to MP4')

    run_yolo = LaunchConfiguration('run_yolo')
    run_fast_scnn = LaunchConfiguration('run_fast_scnn')
    record_mp4 = LaunchConfiguration('record_mp4')

    video_streamer_node = Node(
        package='data_ingestion',
        executable='video_streamer',
        name='video_streamer',
        output='screen'
    )

    yolo_node = Node(
        package='ai_inference',
        executable='yolo_detector_node.py', 
        name='yolo_detector',
        condition=IfCondition(run_yolo),
        output='screen'
    )

    fast_scnn_node = Node(
        package='ai_inference',
        executable='fast_scnn_segmenter_node.py',
        name='fast_scnn_segmenter',
        condition=IfCondition(run_fast_scnn),
        output='screen'
    )

    metric_logger_node = Node(
        package='ai_inference',
        executable='metric_logger.py',
        name='metric_logger',
        output='screen'
    )

    presentation_exporter_node = Node(
        package='visualizer_tools',
        executable='presentation_exporter',
        name='presentation_exporter',
        condition=IfCondition(record_mp4),
        parameters=[
            {'topic_name': 'inference/segmentation_mask'} 
        ],
        output='screen'
    )

    return LaunchDescription([
        run_yolo_arg,
        run_fast_scnn_arg,
        record_mp4_arg,
        video_streamer_node,
        yolo_node,
        fast_scnn_node,
        metric_logger_node,
        presentation_exporter_node
    ])