import os
import sys
sys.path.insert(0, ".")

from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config_loader import ConfigLoader
from src.preprocessor import Preprocessor
from src.geometry import NormalizedGeometry

def test_photoshop_500dpi_reading():
    print("=== Kiểm thử đọc file Photoshop 19.2cm @ 500 DPI ===")
    test_dir = "tests/test_ps_500dpi"
    os.makedirs(test_dir, exist_ok=True)

    # 19.2 cm = 192 mm, 15.2 cm = 152 mm at 500 DPI
    w_px = int(round(192.0 * 500 / 25.4)) # 3780 px
    h_px = int(round(152.0 * 500 / 25.4)) # 2992 px

    ps_img_path = os.path.join(test_dir, "TOI.png")
    img = Image.new("RGBA", (w_px, h_px), (255, 100, 50, 255))
    # Save with embedded 500 DPI metadata (Photoshop standard)
    img.save(ps_img_path, "PNG", dpi=(500, 500))

    import json
    cfg_dict = {
        "canvas": {
            "paper_size": "A3",
            "width_mm": 297.0,
            "height_mm": 420.0,
            "dpi": 150
        },
        "preprocessing": {
            "use_embedded_dpi": True,
            "auto_scale_oversized": False
        }
    }
    cfg_path = "tests/test_config_ps.json"
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f, indent=2)

    config = ConfigLoader(cfg_path)
    preprocessor = Preprocessor(config)
    item = preprocessor.process_file(ps_img_path)

    assert item is not None, "Không đọc được file ảnh Photoshop!"
    geom = NormalizedGeometry(item)

    real_w_mm = config.px_to_mm(geom.orig_w)
    real_h_mm = config.px_to_mm(geom.orig_h)

    print(f"Kích thước sau khi tự phát hiện 500 DPI và quy đổi về Canvas 150 DPI:")
    print(f" -> Pixel canvas: {geom.orig_w}x{geom.orig_h} px")
    print(f" -> Kích thước thực tế: {real_w_mm/10.0:.2f} cm x {real_h_mm/10.0:.2f} cm")

    assert abs(real_w_mm - 192.0) < 5.0, f"LỖI: Chiều ngang thực tế phải là 19.2 cm! Nhưng tính ra {real_w_mm/10.0:.2f} cm"
    print("✔ THÀNH CÔNG: Đã phát hiện chuẩn 500 DPI Photoshop và quy đổi kích thước thực tế chính xác 19.2 cm!")

if __name__ == "__main__":
    test_photoshop_500dpi_reading()
