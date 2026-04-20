import cv2
import os
import numpy as np

def extract_templates():
    """ 从预设截图中自动裁剪并保存常用的按钮识别模板 """

    img_path = "template.png"
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return

    img = cv2.imread(img_path)
    if img is None:
        print(f"Error: Failed to load {img_path}.")
        return

    # Image is 2560x1600.
    # Right-bottom area where buttons are located.
    # We will crop several templates based on the provided image content.
    
    # 1. The biggest 'Skill' button (far right)
    # Coordinates estimated from standard 2560x1600 layout:
    # Right-bottom corner is (2560, 1600).
    # The 'Skill' button is roughly at ~ [2380, 1430] to [2540, 1580]
    skill_btn = img[1430:1580, 2380:2540]
    cv2.imwrite("templates/skill_main.png", skill_btn)
    
    # 2. The 'Capture' button (left of skill)
    # Roughly at ~ [1445, 1450] height, [2240, 2360] width
    capture_btn = img[1445:1565, 2240:2360]
    cv2.imwrite("templates/capture.png", capture_btn)
    
    # 3. The 'Backpack' button 
    # Roughly at ~ [1445, 1450] height, [2110, 2225] width
    bag_btn = img[1445:1565, 2110:2225]
    cv2.imwrite("templates/backpack.png", bag_btn)

    print("Templates extracted to templates/ folder.")

if __name__ == "__main__":
    if not os.path.exists("templates"):
        os.makedirs("templates")
    extract_templates()
