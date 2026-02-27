import os
import cv2

def main():
    print("Scanning dataset for mismatched masks...")
    fixed_count = 0
    
    for split in ['train', 'val']:
        img_dir = f'data/combined_dataset/images/{split}'
        mask_dir = f'data/combined_dataset/annotations/{split}'
        
        if not os.path.exists(img_dir): continue
        
        for img_name in os.listdir(img_dir):
            if not img_name.endswith('.jpg'): continue
            
            img_path = os.path.join(img_dir, img_name)
            img = cv2.imread(img_path)
            
            mask_name = img_name.replace('.jpg', '_mask.png')
            mask_path = os.path.join(mask_dir, mask_name)
            
            if not os.path.exists(mask_path): continue
            
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            
            if mask is not None and img is not None:
                # If the dimensions don't match, fix the mask!
                if mask.shape[:2] != img.shape[:2]:
                    # Resize mask using NEAREST interpolation so class values (1, 2, 3) don't blur
                    mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
                    cv2.imwrite(mask_path, mask)
                    fixed_count += 1
                    print(f"Fixed mismatched mask: {mask_name}")

    print(f"\nDone! Successfully fixed {fixed_count} corrupted masks.")

if __name__ == "__main__":
    main()