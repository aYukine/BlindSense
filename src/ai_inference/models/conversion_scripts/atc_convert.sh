#!/bin/bash

MINDIR_FILE=$1
OUTPUT_NAME=$2

echo "Starting ATC Conversion for $MINDIR_FILE..."

atc --model=$MINDIR_FILE \
    --framework=1 \
    --output=../converted/$OUTPUT_NAME \
    --input_format=NCHW \
    --input_shape="actual_input_1:1,3,720,1280" \
    --soc_version=Ascend310B4 \
    --log=error

echo "Conversion complete: ../converted/$OUTPUT_NAME.om"