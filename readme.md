---
# BlindSense Project
---

## Description
Blindsense is a project that aims to help blind or visually impaired individuals navigate their environment using a combination of sensors and AI algorithms. The system will provide real-time textile feedback to the user.

## Prerequisites
- Linux operating system (Preferably Ubuntu)
- Python >= 3.x
- ROS2 along with its developer tools

## Build and run
Navigate to the project root directory:
```bash
cd /path/to/blindsense
```

Build the project at the root directory:  
```bash
colcon build
```

Source the setup file from the project root directory:
```bash
source setup.bash
```

To launch the project:
```bash
./launch.sh [full/server/client]
```

launch.sh accepts three arguments:
- `full`: Launches both the server and client nodes as standalone hardware.
- `server`: Launches only the server node that will do the heavy processing.
- `client`: Launches only the client node that will process data on the hardware and rely on server for heavy processing.

## Example

I'll update later
I miss you, hasha
