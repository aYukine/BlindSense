_base_ = [
    'configs/pidnet/pidnet-s_2xb6-120k_1024x1024-cityscapes.py'
]

# 2. Dataset Configuration (Dynamic 3-Class Setup)
dataset_type = 'BaseSegDataset'
data_root = 'data/outdoor_dataset/' 
classes = ('background', 'sidewalk', 'road')
palette = [[0, 0, 0], [0, 255, 0], [0, 0, 255]]

crop_size = (224, 224) 

# 3. Pipelines (With GenerateEdge restored)
train_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='LoadAnnotations'),
    dict(type='Resize', scale=crop_size, keep_ratio=False),
    dict(type='RandomFlip', prob=0.5),
    dict(type='GenerateEdge', edge_width=4), 
    dict(type='PackSegInputs')
]

test_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='Resize', scale=crop_size, keep_ratio=False), 
    dict(type='LoadAnnotations'), 
    dict(type='PackSegInputs')
]

# 4. Dataloaders
train_dataloader = dict(
    batch_size=8,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type='InfiniteSampler', shuffle=True),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        data_prefix=dict(img_path='images/train', seg_map_path='annotations/train'),
        seg_map_suffix='_mask.png',
        pipeline=train_pipeline,
        metainfo=dict(classes=classes, palette=palette) # Injects the 3 classes dynamically
    )
)

val_dataloader = dict(
    batch_size=1,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type='DefaultSampler', shuffle=False),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        data_prefix=dict(img_path='images/val', seg_map_path='annotations/val'),
        seg_map_suffix='_mask.png',
        pipeline=test_pipeline,
        metainfo=dict(classes=classes, palette=palette)
    )
)

test_dataloader = val_dataloader
val_evaluator = dict(type='IoUMetric', iou_metrics=['mIoU'])
test_evaluator = val_evaluator

# 5. Model Overrides (Crushing down to 3 classes)
model = dict(
    data_preprocessor=dict(size=crop_size),
    decode_head=dict(
        num_classes=3, 
        loss_decode=[
            dict(type='CrossEntropyLoss', use_sigmoid=False, loss_weight=0.4),
            dict(type='OhemCrossEntropy', thres=0.9, min_kept=5000, loss_weight=1.0),
            dict(type='BoundaryLoss', loss_weight=20.0),
            dict(type='OhemCrossEntropy', thres=0.9, min_kept=5000, loss_weight=1.0)
        ]
    )
)

# 6. Training Schedules & Optimizers (Matching your old code exactly)
optimizer = dict(type='SGD', lr=0.01, momentum=0.9, weight_decay=0.0005)
optim_wrapper = dict(type='OptimWrapper', optimizer=optimizer, clip_grad=None)

train_cfg = dict(type='IterBasedTrainLoop', max_iters=80000, val_interval=4000)
default_hooks = dict(checkpoint=dict(type='CheckpointHook', by_epoch=False, interval=4000))