import json
import os
from typing import Dict, Any, List, Tuple

class ConfigLoader:
    """
    Quản lý 100% tham số ứng dụng từ file JSON cấu hình.
    Tuân thủ quy tắc ZERO HARDCODING.
    """
    MM_PER_INCH = 25.4

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.raw_config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"File cấu hình '{self.config_path}' không tồn tại!")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.raw_config = json.load(f)

    def mm_to_px(self, mm: float) -> float:
        dpi = self.canvas.get("dpi", 300)
        return (mm * dpi) / self.MM_PER_INCH

    def px_to_mm(self, px: float) -> float:
        dpi = self.canvas.get("dpi", 300)
        return (px * self.MM_PER_INCH) / dpi

    @property
    def canvas(self) -> Dict[str, Any]:
        return self.raw_config.get("canvas", {})

    @property
    def preprocessing(self) -> Dict[str, Any]:
        return self.raw_config.get("preprocessing", {})

    @property
    def nesting(self) -> Dict[str, Any]:
        return self.raw_config.get("nesting", {})

    @property
    def sorting(self) -> Dict[str, Any]:
        return self.raw_config.get("sorting", {})

    @property
    def rendering(self) -> Dict[str, Any]:
        return self.raw_config.get("rendering", {})

    @property
    def quality_check(self) -> Dict[str, Any]:
        return self.raw_config.get("quality_check", {})

    @property
    def paths(self) -> Dict[str, Any]:
        return self.raw_config.get("paths", {})

    # Scaled dimensions in pixels
    @property
    def canvas_width_px(self) -> int:
        return int(round(self.mm_to_px(self.canvas["width_mm"])))

    @property
    def canvas_height_px(self) -> int:
        return int(round(self.mm_to_px(self.canvas["height_mm"])))

    @property
    def margin_left_px(self) -> float:
        return self.mm_to_px(self.canvas.get("margin_left_mm", 0.0))

    @property
    def margin_right_px(self) -> float:
        return self.mm_to_px(self.canvas.get("margin_right_mm", 0.0))

    @property
    def margin_top_px(self) -> float:
        return self.mm_to_px(self.canvas.get("margin_top_mm", 0.0))

    @property
    def margin_bottom_px(self) -> float:
        return self.mm_to_px(self.canvas.get("margin_bottom_mm", 0.0))

    @property
    def padding_px(self) -> float:
        return self.mm_to_px(self.nesting.get("padding_mm", 0.0))

    @property
    def printable_bounds_px(self) -> Tuple[float, float, float, float]:
        """(min_x, min_y, max_x, max_y) in pixels"""
        min_x = self.margin_left_px
        min_y = self.margin_top_px
        max_x = self.canvas_width_px - self.margin_right_px
        max_y = self.canvas_height_px - self.margin_bottom_px
        return (min_x, min_y, max_x, max_y)
