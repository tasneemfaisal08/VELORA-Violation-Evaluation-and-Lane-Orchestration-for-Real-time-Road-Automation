import os
import cv2
import albumentations as A

def main():
    # 1. Define the Augmentation Pipeline using Affine (removes the warning)
    transform = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(p=0.2),
        A.Affine(translate_percent={"x": (-0.1, 0.1), "y": (-0.1, 0.1)}, scale=(0.9, 1.1), rotate=(-15, 15), p=0.5),
        A.Blur(blur_limit=3, p=0.2),
        A.RGBShift(r_shift_limit=15, g_shift_limit=15, b_shift_limit=15, p=0.5)
    ], bbox_params=A.BboxParams(
        format='yolo', 
        label_fields=['class_labels'],
        min_visibility=0.3
    ))

    # 2. Hardcoded Absolute Paths (Cleaned from inline comments)
    images_dir = r"C:\Users\Admin\Downloads\traffic light controller\Emergency_vehicles_in_Egypt\train\images"
    labels_dir = r"C:\Users\Admin\Downloads\traffic light controller\Emergency_vehicles_in_Egypt\train\labels"

    # Number of augmented images to generate from each original image
    NUM_AUG_PER_IMAGE = 4 

    # Filter and list all valid images
    image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]

    print("🚀 Starting data augmentation and dataset expansion...")
    
    generated_count = 0

    for img_file in image_files:
        base_name = os.path.splitext(img_file)[0]
        img_path = os.path.join(images_dir, img_file)
        lbl_path = os.path.join(labels_dir, base_name + '.txt')
        
        if not os.path.exists(lbl_path):
            continue
            
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        bboxes = []
        class_labels = []
        with open(lbl_path, 'r') as f:
            for line in f.readlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                cls = int(parts[0])
                x, y, w, h = map(float, parts[1:])
                bboxes.append([x, y, w, h])
                class_labels.append(cls)
                
        for i in range(NUM_AUG_PER_IMAGE):
            try:
                transformed = transform(image=image, bboxes=bboxes, class_labels=class_labels)
                transformed_image = transformed['image']
                transformed_bboxes = transformed['bboxes']
                transformed_labels = transformed['class_labels']
                
                new_img_name = f"{base_name}_aug_{i}.jpg"
                new_img_path = os.path.join(images_dir, new_img_name)
                
                new_lbl_name = f"{base_name}_aug_{i}.txt"
                new_lbl_path = os.path.join(labels_dir, new_lbl_name)
                
                cv2.imwrite(new_img_path, cv2.cvtColor(transformed_image, cv2.COLOR_RGB2BGR))
                
                with open(new_lbl_path, 'w') as f:
                    for box, label in zip(transformed_bboxes, transformed_labels):
                        f.write(f"{label} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f}\n")
                
                generated_count += 1
                
            except Exception as e:
                continue

    print("\n==================================================")
    print("🎉 Data Augmentation Completed Successfully!")
    print(f"Generated {generated_count} new images.")
    print(f"Total training images now available: {len(os.listdir(images_dir))}")
    print("==================================================")

if __name__ == '__main__':
    main()