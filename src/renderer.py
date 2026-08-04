import os
from PIL import Image
from typing import List, Dict, Any
from src.config_loader import ConfigLoader
from src.nesting_engine import A3Sheet, PlacedItem

class RenderEngine:
    """
    Render Engine cho các trang A3:
    - Canvas A3 chuẩn độ phân giải DPI từ config.json
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

        for i, sheet in enumerate(sheets, start=1):
            sheet_image = self.render_sheet(sheet)
            filename = f"A3_{i:03d}.png"
            file_path = os.path.join(output_dir, filename)
            sheet_image.save(file_path, "PNG")
            saved_paths.append(file_path)
            print(f"Đã xuất ảnh trang A3: {file_path}")

        return saved_paths
