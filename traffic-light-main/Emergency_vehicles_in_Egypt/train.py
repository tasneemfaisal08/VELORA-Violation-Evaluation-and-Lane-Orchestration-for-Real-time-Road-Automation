import os
from ultralytics import YOLO

def main():
    yaml_path = r"C:\Users\Admin\Downloads\traffic light controller\Emergency_vehicles_in_Egypt\data.yaml" 
    
    print("🔄 Loading pretrained YOLOv8m model...")
    model = YOLO('yolov8m.pt')

    print("\n🚀 Restarting Training...")
    model.train(
        data=yaml_path,       
        epochs=100,           
        imgsz=640,            
        batch=8,              
        workers=2,            
        device=0,  # لو مفيش كارت شاشة NVIDIA خليه 'cpu'
        freeze=10, # تجميد الطبقات لحماية الكلاسات العالمية
        mosaic=1.0,           
        name='egypt_emergency_v8_final'  
    )
    print("\n🎉 Training Finished! The 'runs' folder has been recreated.")

if __name__ == '__main__':
    main()