import os
from PIL import Image, ImageDraw

def create_icon(size, filename):
    # Deep dark blue background
    img = Image.new('RGB', (size, size), color=(13, 18, 40))
    d = ImageDraw.Draw(img)
    
    # Draw a simple 'Greek' Omega symbol or a stylized graph
    # Let's just draw an accent colored circle and a chart line
    center = size // 2
    radius = size // 3
    
    # Outer circle
    d.ellipse((center - radius, center - radius, center + radius, center + radius), 
              outline=(59, 130, 246), width=size // 20)
              
    # Fake chart line
    points = [
        (size*0.3, size*0.6),
        (size*0.5, size*0.4),
        (size*0.7, size*0.45),
        (size*0.8, size*0.3)
    ]
    d.line(points, fill=(245, 158, 11), width=size // 15)

    os.makedirs('icons', exist_ok=True)
    img.save(f'icons/{filename}')
    print(f"Generated icons/{filename}")

if __name__ == '__main__':
    create_icon(192, 'icon-192.png')
    create_icon(512, 'icon-512.png')
