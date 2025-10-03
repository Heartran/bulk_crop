from PIL import Image
import os

# coordinate precise
LEFT, TOP = 1381, 119
SIZE = 273
RIGHT = LEFT + SIZE
BOTTOM = TOP + SIZE

input_folder = 'input'
output_folder = 'output'
os.makedirs(output_folder, exist_ok=True)

for fname in os.listdir(input_folder):
    if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue
    img = Image.open(os.path.join(input_folder, fname))
    cropped = img.crop((LEFT, TOP, RIGHT, BOTTOM))
    cropped.save(os.path.join(output_folder, fname))
    print(f"✔️ {fname} ritagliata")
