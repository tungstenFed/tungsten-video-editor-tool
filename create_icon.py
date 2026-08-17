#!/usr/bin/env python3
"""Create a simple app icon."""
from PIL import Image, ImageDraw
import os

# Create a 256x256 icon with Dracula theme colors
size = 256
img = Image.new('RGBA', (size, size), (40, 42, 54, 255))  # Dracula background
draw = ImageDraw.Draw(img)

# Colors
purple = (189, 147, 249)  # Dracula purple
cyan = (139, 233, 253)    # Dracula cyan
bg_dark = (33, 34, 44)    # Dracula bg_alt

# Draw rounded rectangle background
margin = 20
radius = 30
draw.rounded_rectangle(
    [margin, margin, size - margin, size - margin],
    radius=radius,
    fill=bg_dark,
    outline=purple,
    width=4
)

# Draw a play triangle in the center
center_x, center_y = size // 2, size // 2
triangle_size = 60
draw.polygon([
    (center_x - triangle_size // 2, center_y - triangle_size // 2),
    (center_x - triangle_size // 2, center_y + triangle_size // 2),
    (center_x + triangle_size // 2, center_y),
], fill=purple)

# Draw a small waveform bars
bar_width = 8
bar_gap = 4
num_bars = 5
start_x = center_x + triangle_size // 2 + 20
for i in range(num_bars):
    bar_height = 20 + (i % 3) * 15
    x = start_x + i * (bar_width + bar_gap)
    y = center_y
    draw.rectangle(
        [x, y - bar_height // 2, x + bar_width, y + bar_height // 2],
        fill=cyan
    )

# Save as ICO with multiple sizes
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
images = []
for icon_size in icon_sizes:
    resized = img.resize(icon_size, Image.Resampling.LANCZOS)
    images.append(resized)

output_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
images[0].save(
    output_path,
    format='ICO',
    sizes=[(im.width, im.height) for im in images],
    append_images=images[1:]
)

print(f"Icon created at: {output_path}")