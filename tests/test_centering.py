import os
import sys
sys.path.insert(0, ".")

from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config_loader import ConfigLoader
from src.preprocessor import Preprocessor
from src.geometry import NormalizedGeometry
from src.nesting_engine import NestingEngine

def test_layout_auto_centering():
    print("=== Kiểm thử tính năng tự động CĂN GIỮA hình trên tờ giấy ===")

    test_dir = "tests/test_png_center"
    os.makedirs(test_dir, exist_ok=True)

    # 150mm x 150mm test image at 150 DPI
    w_px = int(round(150.0 * 150 / 25.4))
    h_px = int(round(150.0 * 150 / 25.4))

    item_path = os.path.join(test_dir, "center_square.png")
    img = Image.new("RGBA", (w_px, h_px), (0, 200, 100, 255))
    img.save(item_path, "PNG")

    import json
    cfg_dict = {
        "canvas": {
            "paper_size": "Custom",
            "width_mm": 390.0,
            "height_mm": 290.0,
            "dpi": 150,
            "margin_top_mm": 0.0,
            "margin_bottom_mm": 0.0,
            "margin_left_mm": 0.0,
            "margin_right_mm": 0.0
        },
        "preprocessing": {
            "auto_scale_oversized": False
        },
        "nesting": {
            "center_layout": True,
            "center_in_printable_area": True,
            "rotation_step_deg": 90,
            "rotation_angles_deg": [0, 90, 180, 270]
        },
        "quality_check": {
            "tolerance_px": 2.0
        }
    }
    cfg_path = "tests/test_config_center.json"
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f, indent=2)

    config = ConfigLoader(cfg_path)
    preprocessor = Preprocessor(config)
    raw_items = preprocessor.load_all_from_folder(test_dir)
    normalized_items = [NormalizedGeometry(i) for i in raw_items]

    nesting_engine = NestingEngine(config)
    sheets = nesting_engine.nest_all(normalized_items)

    sheet = sheets[0]
    placed_min_x = min(item.x for item in sheet.placed_items)
    placed_max_x = max(item.x + item.rot_w for item in sheet.placed_items)
    placed_min_y = min(item.y for item in sheet.placed_items)
    placed_max_y = max(item.y + item.rot_h for item in sheet.placed_items)

    left_margin_px = placed_min_x - sheet.min_x
    right_margin_px = sheet.max_x - placed_max_x
    top_margin_px = placed_min_y - sheet.min_y
    bottom_margin_px = sheet.max_y - placed_max_y

    left_margin_mm = config.px_to_mm(left_margin_px)
    right_margin_mm = config.px_to_mm(right_margin_px)
    top_margin_mm = config.px_to_mm(top_margin_px)
    bottom_margin_mm = config.px_to_mm(bottom_margin_px)

    print(f"Khoảng cách mép Trái: {left_margin_mm:.2f} mm | Mép Phải: {right_margin_mm:.2f} mm")
    print(f"Khoảng cách mép Trên: {top_margin_mm:.2f} mm | Mép Dưới: {bottom_margin_mm:.2f} mm")

    assert abs(left_margin_mm - right_margin_mm) < 0.5, f"LỖI: Mép trái ({left_margin_mm:.2f}mm) và Mép phải ({right_margin_mm:.2f}mm) phải bằng nhau!"
    assert abs(top_margin_mm - bottom_margin_mm) < 0.5, f"LỖI: Mép trên ({top_margin_mm:.2f}mm) và Mép dưới ({bottom_margin_mm:.2f}mm) phải bằng nhau!"

    print("✔ THÀNH CÔNG: Toàn bộ hình đã được căn giữa tuyệt đối, cách đều các mép Trái/Phải và Trên/Dưới!")

if __name__ == "__main__":
    test_layout_auto_centering()
