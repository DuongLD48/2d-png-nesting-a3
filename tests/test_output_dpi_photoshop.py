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
from src.renderer import RenderEngine

def test_export_500dpi_photoshop_size():
    print("=== Kiểm thử xuất file PNG 390x290 mm chuẩn 500 DPI cho Photoshop ===")

    test_dir = "tests/test_output_500dpi"
    output_dir = "tests/output_500dpi"
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 190mm x 150mm item at 500 DPI
    w_px = int(round(190.0 * 500 / 25.4))
    h_px = int(round(150.0 * 500 / 25.4))

    item_path = os.path.join(test_dir, "test_item.png")
    img = Image.new("RGBA", (w_px, h_px), (255, 0, 0, 255))
    img.save(item_path, "PNG", dpi=(500, 500))

    import json
    cfg_dict = {
        "canvas": {
            "paper_size": "Custom",
            "width_mm": 390.0,
            "height_mm": 290.0,
            "dpi": 500,
            "margin_top_mm": 0.0,
            "margin_bottom_mm": 0.0,
            "margin_left_mm": 0.0,
            "margin_right_mm": 0.0
        },
        "preprocessing": {
            "use_embedded_dpi": True,
            "auto_scale_oversized": False
        },
        "nesting": {
            "padding_mm": 3.0,
            "enable_360_rotation": True,
            "rotation_step_deg": 15
        },
        "quality_check": {
            "tolerance_px": 2.0
        }
    }
    cfg_path = "tests/test_config_500dpi.json"
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f, indent=2)

    config = ConfigLoader(cfg_path)
    preprocessor = Preprocessor(config)
    raw_items = preprocessor.load_all_from_folder(test_dir)
    normalized_items = [NormalizedGeometry(i) for i in raw_items]

    nesting_engine = NestingEngine(config)
    sheets = nesting_engine.nest_all(normalized_items)

    renderer = RenderEngine(config)
    out_paths = renderer.render_and_save_all(sheets, output_dir)

    out_file = out_paths[0]
    exported_img = Image.open(out_file)
    dpi_info = exported_img.info.get("dpi")
    w_out_px, h_out_px = exported_img.size

    print(f"File xuất ra: {out_file}")
    print(f" -> Resolution (Metadata DPI): {dpi_info}")
    print(f" -> Pixel resolution: {w_out_px} x {h_out_px} px")

    out_dpi_x = dpi_info[0] if dpi_info else 72.0
    out_dpi_y = dpi_info[1] if dpi_info else 72.0

    physical_w_cm = (w_out_px / out_dpi_x) * 2.54
    physical_h_cm = (h_out_px / out_dpi_y) * 2.54

    print(f" -> Kích thước Photoshop nhận dạng được: {physical_w_cm:.2f} cm x {physical_h_cm:.2f} cm @ {out_dpi_x:.0f} DPI")

    assert dpi_info is not None and abs(out_dpi_x - 500.0) < 1.0, f"LỖI: Metadata DPI phải là 500! Nhưng file ra có DPI = {dpi_info}"
    assert abs(physical_w_cm - 39.0) < 0.5, f"LỖI: Chiều ngang khi mở trong Photoshop phải là 39.0 cm! Nhưng tính ra {physical_w_cm:.2f} cm"
    assert abs(physical_h_cm - 29.0) < 0.5, f"LỖI: Chiều cao khi mở trong Photoshop phải là 29.0 cm! Nhưng tính ra {physical_h_cm:.2f} cm"

    print("✔ THÀNH CÔNG RỰC RỠ: File xuất ra có đúng 500 DPI và mở trong Photoshop hiển thị chính xác 39.0 cm x 29.0 cm!")

if __name__ == "__main__":
    test_export_500dpi_photoshop_size()
