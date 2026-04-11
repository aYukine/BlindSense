import mindspore as ms
import mindspore.nn as nn
import mindspore.ops as ops

class ConvBNReLU(nn.Cell):
    """Standard Convolution -> BatchNorm -> ReLU block"""
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1, groups=1):
        super(ConvBNReLU, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, 
                              pad_mode='pad', padding=padding, group=groups, has_bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()

    def construct(self, x):
        return self.relu(self.bn(self.conv(x)))

class DepthwiseSeparableConv(nn.Cell):
    """Depthwise Separable Convolution for efficiency"""
    def __init__(self, in_channels, out_channels, stride=1):
        super(DepthwiseSeparableConv, self).__init__()
        self.depthwise = ConvBNReLU(in_channels, in_channels, 3, stride, 1, groups=in_channels)
        self.pointwise = ConvBNReLU(in_channels, out_channels, 1, 1, 0)

    def construct(self, x):
        return self.pointwise(self.depthwise(x))

class LearningToDownsample(nn.Cell):
    """Extracts low-level details and reduces spatial resolution"""
    def __init__(self, in_channels, out_channels):
        super(LearningToDownsample, self).__init__()
        self.conv1 = ConvBNReLU(in_channels, 32, kernel_size=3, stride=2, padding=1)
        self.dsconv1 = DepthwiseSeparableConv(32, 48, stride=2)
        self.dsconv2 = DepthwiseSeparableConv(48, out_channels, stride=2)

    def construct(self, x):
        return self.dsconv2(self.dsconv1(self.conv1(x)))

class FeatureFusionModule(nn.Cell):
    """Fuses high-res low-level features with low-res high-level features"""
    def __init__(self, higher_in_channels, lower_in_channels, out_channels):
        super(FeatureFusionModule, self).__init__()
        self.dwconv = ConvBNReLU(lower_in_channels, out_channels, kernel_size=3, padding=1, groups=out_channels)
        self.conv_lower = nn.Conv2d(out_channels, out_channels, kernel_size=1, has_bias=False)
        self.bn_lower = nn.BatchNorm2d(out_channels)
        
        self.conv_higher = nn.Conv2d(higher_in_channels, out_channels, kernel_size=1, has_bias=False)
        self.bn_higher = nn.BatchNorm2d(out_channels)
        
        self.relu = nn.ReLU()

    def construct(self, higher_res_feature, lower_res_feature):
        lower_res = self.dwconv(lower_res_feature)
        lower_res = self.bn_lower(self.conv_lower(lower_res))
        
        # Resize lower_res to match higher_res spatial dimensions
        target_size = higher_res_feature.shape[2:] 
        lower_res_upsampled = ops.interpolate(lower_res, size=target_size, mode='bilinear', align_corners=True)
        
        higher_res = self.bn_higher(self.conv_higher(higher_res_feature))
        
        # Add them together
        return self.relu(lower_res_upsampled + higher_res)

class FastSCNN(nn.Cell):
    """Complete Fast S-CNN Architecture"""
    def __init__(self, num_classes, in_channels=3):
        super(FastSCNN, self).__init__()
        
        # 1. Learning to Downsample (Output is 1/8th of input size)
        self.learning_to_downsample = LearningToDownsample(in_channels, 64)
        
        # 2. Global Feature Extractor
        self.global_feature_extractor = nn.SequentialCell([
            DepthwiseSeparableConv(64, 64, stride=2),
            DepthwiseSeparableConv(64, 96, stride=1),
            DepthwiseSeparableConv(96, 128, stride=2),
            DepthwiseSeparableConv(128, 128, stride=1)
        ])
        
        # 3. Feature Fusion Module
        self.feature_fusion = FeatureFusionModule(higher_in_channels=64, lower_in_channels=128, out_channels=128)
        
        # 4. Classifier
        self.classifier = nn.SequentialCell([
            DepthwiseSeparableConv(128, 128, stride=1),
            nn.Conv2d(128, num_classes, kernel_size=1, has_bias=True)
        ])

    def construct(self, x):
        # Save original size for final upsampling
        original_size = x.shape[2:]
        
        # Branch 1: High-res details
        higher_res_features = self.learning_to_downsample(x)
        
        lower_res_features = self.global_feature_extractor(higher_res_features)
        
        fused_features = self.feature_fusion(higher_res_features, lower_res_features)
        
        out = self.classifier(fused_features)
        
        out = ops.interpolate(out, size=original_size, mode='bilinear', align_corners=True)
        return out

if __name__ == "__main__":
    ms.set_context(mode=ms.PYNATIVE_MODE, device_target="GPU")
    
    NUM_CLASSES = 3 
    
    print("Initializing Fast S-CNN model from src...")
    model = FastSCNN(num_classes=NUM_CLASSES)
    
    dummy_input = ops.ones((2, 3, 512, 1024), ms.float32)
    
    print(f"Feeding input of shape: {dummy_input.shape} into the network...")
    output = model(dummy_input)
    
    print("Model Test passed!")
    print(f"Output Tensor Shape: {output.shape}")