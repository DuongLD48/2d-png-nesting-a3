import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def create_star_png(filepath, size=300, num_points=5, color=(255, 87, 34, 255)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    r_outer = size * 0.45
    r_inner = size * 0.2

    points = []
    for i in range(2 * num_points):
        r = r_outer if i % 2 == 0 else r_inner
        angle = i * math.pi / num_points - math.pi / 2
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))

    draw.polygon(points, fill=color)
    img.save(filepath, "PNG")

def create_l_shape_png(filepath, width=350, height=250, thickness=80, color=(33, 150, 243, 255)):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [
        (0, 0),
        (thickness, 0),
        (thickness, height - thickness),
        (width, height - thickness),
        (width, height),
        (0, height)
    ]
    draw.polygon(pts, fill=color)
    img.save(filepath, "PNG")

def create_circle_png(filepath, diameter=220, color=(76, 175, 80, 255)):
    img = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, diameter, diameter), fill=color)
    img.save(filepath, "PNG")

def create_triangle_png(filepath, width=280, height=220, color=(156, 39, 176, 255)):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [(width / 2, 0), (width, height), (0, height)]
    draw.polygon(pts, fill=color)
    img.save(filepath, "PNG")

def create_rect_png(filepath, width=320, height=180, color=(255, 193, 7, 255)):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, height), fill=color)
    img.save(filepath, "PNG")

def generate_all_test_pngs(output_dir="pngfile"):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Đang sinh danh sách file ảnh PNG mẫu vào thư mục '{output_dir}'...")

    shapes = [
        ("shape_01_star_lg.png", lambda p: create_star_png(p, size=320, num_points=6, color=(244, 67, 54, 255))),
        ("shape_02_lshape.png", lambda p: create_l_shape_png(p, width=380, height=280, thickness=90, color=(33, 150, 243, 255))),
        ("shape_03_rect_long.png", lambda p: create_rect_png(p, width=420, height=120, color=(255, 152, 0, 255))),
        ("shape_04_circle.png", lambda p: create_circle_png(p, diameter=250, color=(76, 175, 80, 255))),
        ("shape_05_triangle.png", lambda p: create_triangle_png(p, width=300, height=240, color=(156, 39, 176, 255))),
        ("shape_06_star_sm.png", lambda p: create_star_png(p, size=200, num_points=5, color=(233, 30, 99, 255))),
        ("shape_07_rect_sq.png", lambda p: create_rect_png(p, width=220, height=220, color=(0, 188, 212, 255))),
        ("shape_08_lshape_sm.png", lambda p: create_l_shape_png(p, width=250, height=200, thickness=60, color=(63, 81, 181, 255))),
        ("shape_09_circle_sm.png", lambda p: create_circle_png(p, diameter=160, color=(139, 195, 74, 255))),
        ("shape_10_triangle_sm.png", lambda p: create_triangle_png(p, width=200, height=180, color=(121, 85, 72, 255))),
        ("shape_11_star_huge.png", lambda p: create_star_png(p, size=400, num_points=7, color=(103, 58, 183, 255))),
        ("shape_12_rect_tall.png", lambda p: create_rect_png(p, width=140, height=360, color=(0, 150, 136, 255))),
    ]

    for filename, fn in shapes:
        fp = os.path.join(output_dir, filename)
        fn(fp)
        print(f" + Đã tạo {filename}")

if __name__ == "__main__":
    generate_all_test_pngs()
