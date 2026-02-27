from mmseg.registry import DATASETS
from .basesegdataset import BaseSegDataset

@DATASETS.register_module()
class CombinedRoadDataset(BaseSegDataset):
    METAINFO = dict(
        classes=('background', 'floor', 'sidewalk', 'road'),
        # Colors: Black, Red, Green, Blue
        palette=[[0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255]] 
    )
    def __init__(self, **kwargs):
        super().__init__(img_suffix='.jpg', seg_map_suffix='_mask.png', **kwargs)