from PIL import Image, ImageDraw
import os

sizes = [72, 96, 128, 144, 152, 192, 384, 512]
for size in sizes:
    img = Image.new('RGB', (size, size), color='#2563eb')
    draw = ImageDraw.Draw(img)
    # Draw a white store icon shape (simple)
    draw.rectangle([size//4, size//4, 3*size//4, 3*size//4], fill='white', outline=None)
    img.save(f'static/icons/icon-{size}x{size}.png')
    print(f"Generated icon-{size}x{size}.png")
