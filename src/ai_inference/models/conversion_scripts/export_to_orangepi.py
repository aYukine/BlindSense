#!/usr/bin/env python3
import argparse
import mindspore as ms
import numpy as np

# Import your exact model definition!
from src.fast_scnn import FastSCNN 

def export_model(ckpt_path, output_name, num_classes):
    print(f"Loading MindSpore checkpoint: {ckpt_path}")
    
    net = FastSCNN(num_classes=num_classes) 
    
    param_dict = ms.load_checkpoint(ckpt_path)
    ms.load_param_into_net(net, param_dict)
    
    dummy_input = ms.Tensor(np.ones([1, 3, 720, 1280]), ms.float32)
    
    export_path = f"../converted/{output_name}" 
    ms.export(net, dummy_input, file_name=export_path, file_format="MINDIR")
    
    print(f"Successfully exported intermediate model to: {export_path}.mindir")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ckpt', type=str, required=True, help='Path to .ckpt file')
    parser.add_argument('--name', type=str, required=True, help='Output name')
    parser.add_argument('--classes', type=int, default=3, help='Number of classes the model was trained on')
    args = parser.parse_args()
    
    # Tell MindSpore we are running on CPU for the export process
    ms.set_context(mode=ms.GRAPH_MODE, device_target="CPU")
    
    export_model(args.ckpt, args.name, args.classes)