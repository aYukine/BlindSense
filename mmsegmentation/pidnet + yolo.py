import cv2
import torch
import numpy as np
import types
from mmseg.apis import MMSegInferencer
from ultralytics import YOLO

# ==========================================
# PYTORCH 2.6 COMPATIBILITY FIX
# ==========================================
_original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = patched_load

# ==========================================
# CONFIGURATION
# ==========================================
VIDEO_PATH = 'video_2026-02-26_18-10-46.mp4'  

YOLO_WEIGHTS = 'work_dirs/best.pt'

PIDNET_CFG = 'pidnet_s_master_outdoor.py' 
PIDNET_WEIGHTS = 'work_dirs/pidnet_s_outdoor/pidnet_outdoor_deploy.pth'

def main():
    # 1. Hardware Check
    if torch.backends.mps.is_available():
        device = 'mps'
        print("Apple Silicon detected! Running on MPS (GPU).")
    else:
        device = 'cpu'
        print("Running on CPU.")

    # 2. Load Models
    print("Loading YOLO Model...")
    yolo_model = YOLO(YOLO_WEIGHTS)
    yolo_model.to(device)

    print("Loading PIDNet Model...")
    pidnet_model = MMSegInferencer(
        model=PIDNET_CFG, 
        weights=PIDNET_WEIGHTS, 
        classes=('background', 'sidewalk', 'road'), 
        palette=[[0, 0, 0], [0, 255, 0], [0, 0, 255]], 
        device=device
    )

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Error: Could not open video '{VIDEO_PATH}'. Please check the file path.")
        return

    print("\nHybrid Pipeline Live! Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video stream.")
            break

        yolo_results = yolo_model(frame, verbose=False) 
        pid_result = pidnet_model(frame, return_datasamples=True)
        
        if isinstance(pid_result, types.GeneratorType):
            pid_result = next(pid_result)
        if isinstance(pid_result, dict) and 'predictions' in pid_result:
            data_sample = pid_result['predictions']
        else:
            data_sample = pid_result 

        pid_mask = data_sample.pred_sem_seg.data[0].cpu().numpy()
        
        color_mask = np.zeros_like(frame)
        color_mask[pid_mask == 1] = [0, 255, 0] # Sidewalk = Green
        color_mask[pid_mask == 2] = [255, 0, 0] # Road = Blue

        # Blend PIDNet colors with the raw video frame
        pidnet_base_canvas = cv2.addWeighted(frame, 1.0, color_mask, 0.4, 0)

        final_frame = yolo_results[0].plot(img=pidnet_base_canvas)
        
        # ====================================================

        cv2.putText(final_frame, " PIDNet + Yolo", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imshow('Real-Time Perception Pipeline', final_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()