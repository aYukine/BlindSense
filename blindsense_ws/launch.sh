#!/bin/bash

# Source ROS 2 and your workspace
source /opt/ros/$ROS_DISTRO/setup.bash
source "$(dirname "$0")/install/setup.bash"

case "$1" in
  full)
    ros2 launch blindsense_launcher blindsense_full_launch.py
    ;;
  client)
    ros2 launch blindsense_launcher blindsense_client_launch.py
    ;;
  server)
    ros2 launch blindsense_launcher blindsense_server_launch.py
    ;;
  *)
    echo "Usage: $0 {full|client|server}"
    exit 1
    ;;
esac