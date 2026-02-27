#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <package_name>"
    exit 1
fi

colcon build --packages-select "$1"

source install/setup.bash

echo "Package '$1' built and sourced successfully."