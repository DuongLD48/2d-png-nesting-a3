import os
import sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config_loader import ConfigLoader
from src.preprocessor import Preprocessor
from src.geometry import NormalizedGeometry
from src.sorter import PrioritySorter
from src.nesting_engine import NestingEngine

def test_40x30_with_two_19x29_images():
    print("=== Đang kiểm thử trường hợp: Khổ 40x30 cm với 2 ảnh 19x29 cm ===")

    # Create dummy folder
    test_dir = "tests/test_png_40x30"
    os.makedirs(test_dir, exist_ok=True)

    # DPI = 150 -> 190mm = 1122px, 290mm = 1713px
    dpi = 150
    w_px = int(round(190.0 * dpi / 25.4))
    h_px = int(round(290.0 * dpi / 25.4))

    # Create 2 test PNGs
    img1 = Image.new("RGBA", (w_px, h_px), (255, 0, 0, 255))
    img1.save(os.path.join(test_dir, "img1_19x29.png"))

    img2 = Image.new("RGBA", (w_px, h_px), (0, 0, 255, 255))
    img2.save(os.path.join(test_dir, "img2_19x29.png"))

    # Config for 40x30 cm paper
    config_dict = {
        "canvas": {
            "paper_size": "40x30cm",
            "width_mm": 400.0,
            "height_mm": 300.0,
            "dpi": 150,
            "margin_top_mm": 5.0,
            "margin_bottom_mm": 5.0,
            "margin_left_mm": 5.0,
            "margin_right_mm": 5.0,
            "background_color_rgba": [255, 255, 255, 0]
        },
        "preprocessing": {
            "alpha_threshold": 10,
            "auto_scale_oversized": False
        },
        "nesting": {
            "padding_mm": 3.0,
            "enable_360_rotation": True,
            "rotation_step_deg": 90,
            "rotation_angles_deg": [0, 90, 180, 270],
            "search_step_px": 10
        },
        "sorting": {
            "primary_key": "area",
            "reverse": True
        },
        "quality_check": {
            "allow_overlap": False,
            "enforce_margins": True,
            "tolerance_px": 2.0
        },

        "paths": {
            "input_folder": test_dir,
            "output_folder": "output_test"
        }
    }

    import json
    cfg_file = "tests/test_config_40x30.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2)

    config = ConfigLoader(cfg_file)
    preprocessor = Preprocessor(config)
    raw_items = preprocessor.load_all_from_folder(test_dir)
    normalized_items = [NormalizedGeometry(item) for item in raw_items]

    sorter = PrioritySorter(config)
    sorted_items = sorter.sort(normalized_items)

    nesting_engine = NestingEngine(config)
    sheets = nesting_engine.nest_all(sorted_items)

    print(f"-> Số trang kết quả: {len(sheets)}")
    for i, s in enumerate(sheets, start=1):
        print(f"   Trang {i}: chứa {len(s.placed_items)} hình")
        for item in s.placed_items:
            print(f"     - File '{item.item_id}' góc xoay: {item.rotation_deg}° tại x={item.x:.1f}, y={item.y:.1f} (Size px: {item.rot_w:.1f}x{item.rot_h:.1f})")

    assert len(sheets) == 1, f"LỖI: 2 hình 19x29 cm trên khổ 40x30 cm phải được xếp gọn vào 1 TRANG DUY NHẤT! Nhưng kết quả sinh ra {len(sheets)} trang!"
    print("✔ THÀNH CÔNG: Cả 2 hình 19x29 cm đã tự động xoay dọc và vừa khít trên 1 TRANG 40x30 cm duy nhất!")

if __name__ == "__main__":
    test_40x30_with_two_19x29_images()
