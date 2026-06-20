import os
from ultralytics import YOLO

def main():
    # 🎯 FORCE it to use the new final weights folder we just generated
    model_path = r"C:\Users\Admin\Downloads\traffic light controller\runs\detect\egypt_emergency_v8_final\weights\best.pt"
    
    if not os.path.exists(model_path):
        print(f"⚠️ Custom weights not found at: {model_path}")
        print("Please verify your exact directory folder names under runs/detect/")
        return

    # Load the fresh model
    model = YOLO(model_path)

    # 🔍 Verification step: This prints exactly what class mapping is inside your weights file
    print("\n🔍 Current Model Class Structure:")
    print(model.names) 
    print("====================================")

    # Path to your test image
    test_image = r"c:\Users\Admin\Pictures\Screenshots\Screenshot 2026-06-15 091845.png"

    if os.path.exists(test_image):
        print("🎯 Processing image using fresh custom weights...")
        # Run clean inference (No manual dictionary overrides!)
        results = model.predict(source=test_image, save=True, conf=0.25)
        print(f"\n✓ Done! Check your final correct image output in: {results[0].save_dir}")
    else:
        print(f"⚠️ Test image not found at: {test_image}")

if __name__ == '__main__':
    main()