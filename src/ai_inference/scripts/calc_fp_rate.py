#!/usr/bin/env python3
# Compare inference output vs ground-truth annotations in your dataset
# Requires: blindsense_perfect_dataset2 annotations in COCO/CSV format
import pandas as pd, json, sys
# Load your inference results (export from ROS 2 bag or CSV)
# Load ground truth annotations
# Compute precision/recall/F1
# Output: false_positive_rate = FP / (FP + TP)
print("✅ Run this after collecting inference outputs with timestamps aligned to dataset frames")