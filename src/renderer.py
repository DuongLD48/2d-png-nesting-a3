import os
from PIL import Image
from typing import List, Dict, Any
from src.config_loader import ConfigLoader
from src.nesting_engine import A3Sheet, PlacedItem

class RenderEngine:
    """
    Render Engine cho các trang A3 / Custom Canvas:
    - Canvas chuẩn độ phân giải DPI từ config.json (mặc định 500 DPI)
    - Nhúng chính xác metadata DPI vào file PNG đầu ra (Photoshop hiển thị chuẩn 500 DPI & đúng kích thước mm)
    - Dán ảnh PNG đã xoay trực tiếp theo ma trận chuẩn từ Nesting Engine
    - Alpha Blending hoàn hảo
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def render_sheet(self, sheet: A3Sheet) -> Image.Image:
        w_px = sheet.width_px
        h_px = sheet.height_px
        
        bg_rgba = tuple(self.config.canvas.get("background_color_rgba", [255, 255, 255, 0]))
        canvas = Image.new("RGBA", (w_px, h_px), bg_rgba)

        for placed in sheet.placed_items:
            rot_pil = placed.rot_pil
            paste_x = int(round(placed.x))
            paste_y = int(round(placed.y))

            # Alpha composite onto canvas
            canvas.alpha_composite(rot_pil, dest=(paste_x, paste_y))

        return canvas

    def render_and_save_all(self, sheets: List[A3Sheet], output_dir: str) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        saved_paths = []
        target_dpi = float(self.config.canvas.get("dpi", 500))

        for i, sheet in enumerate(sheets, start=1):
            sheet_image = self.render_sheet(sheet)
            filename = f"A3_{i:03d}.png"
            file_path = os.path.join(output_dir, filename)
            
            # Save PNG with embedded DPI metadata (Photoshop / Printing standard)
            sheet_image.save(file_path, "PNG", dpi=(target_dpi, target_dpi))
            saved_paths.append(file_path)
            
            w_mm = self.config.canvas.get("width_mm")
            h_mm = self.config.canvas.get("height_mm")
            print(f"Đã xuất ảnh trang A3: {file_path} (Kích thước: {w_mm}x{h_mm} mm @ {target_dpi:.0f} DPI)")

        return saved_paths
