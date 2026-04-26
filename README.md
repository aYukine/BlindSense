# BlindSense: Real-Time Edge AI Spatial Perception System

BlindSense is an assistive spatial perception robotics stack designed to provide real-time environmental awareness for visually impaired users. Built on ROS 2, the system fuses 2D Semantic Segmentation, Object Detection, and 3D Point Cloud geometry to dynamically route obstacle proximity data to a localized haptic feedback array.

This repository contains a highly optimized, bare-metal deployment architecture specifically engineered for the **Orange Pi AI Pro (Huawei Ascend NPU)**, overcoming severe low-power ARM CPU bottlenecks.

## Hardware Architecture
* **Compute:** Orange Pi AI Pro (20 TOPS Ascend NPU, ARM Cortex-A CPU)
* **Sensor:** Stereo Camera (RGB-D)
* **Feedback:** 3-Zone PWM Haptic Actuator Array

## AI Models & Frameworks
* **Semantic Segmentation:** Fast-SCNN (Custom trained, MindSpore `.om` export)
* **Object Detection:** YOLOv8 (Ultralytics, Ascend `.om` export)
* **Middleware:** ROS 2 (Humble/Iron)
* **Vision & 3D:** OpenCV DNN, Point Cloud Library (PCL), Ascend Computing Language (ACL)

## Key Edge Optimizations (The "Host-to-Device" Solution)
Standard deployments of PyTorch or Ultralytics on edge NPUs often result in **NPU Starvation**—where the AI accelerator sits idle while the low-power ARM CPU struggles to execute Python-based image normalization (`numpy`) and array transpositions. 

To achieve real-time 30 FPS inference, this stack implements aggressive Host-side optimizations:
1. **Bare-Metal NPU Execution:** Completely bypassed heavy PyTorch/Ultralytics middleware. Models are loaded directly into silicon via Huawei Ascend ACL `acl.mdl.execute`.
2. **C++ Accelerated Tensor Prep:** Replaced slow Python `numpy` loops with OpenCV's C++ deep learning backend (`cv2.dnn.blobFromImage`), reducing tensor normalization and transposition latency from ~1,500ms down to ~15ms.
3. **C++ Accelerated NMS:** Offloaded YOLO Non-Maximum Suppression to OpenCV's `cv2.dnn.NMSBoxes`, bypassing Python loops.
4. **Vectorized Look-Up Tables (LUT):** Replaced boolean indexing arrays with pre-allocated C-level LUTs for instant semantic mask colorization.
5. **Aggressive Spatial Downsampling:** Optimized the C++ `depth_estimator_node` to downsample raw depth maps (Step=8), reducing Point Cloud generation from 230,000 points to 14,400 points, dropping CPU load by >60% while maintaining dense haptic accuracy.

## Package Architecture
* `ai_inference`: Bare-metal Python/ACL nodes for Fast-SCNN and YOLO execution.
* `perception_3d`: High-speed C++ nodes for depth projection and spatial zone slicing (Left/Center/Right).
* `haptic_decision`: Converts segmented spatial distances into physical PWM actuator intensities.
* `data_ingestion`: Pipeline for live RealSense capture and Huawei DVPP/AIPP hardware wrappers.
* `system_launch`: Master orchestration for synchronized node bring-up.
* `visualizer_tools`: MP4 presentation and diagnostic rendering tools.

## Build and Run Instructions

### 1. Build the Workspace
Ensure you have sourced your ROS 2 environment and the Huawei Ascend Toolkit.
```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
colcon build --symlink-install
source install/setup.bash
