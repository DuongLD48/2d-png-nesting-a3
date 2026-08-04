from typing import List
from src.geometry import NormalizedGeometry
from src.config_loader import ConfigLoader

class PrioritySorter:
    """
    Sắp xếp danh sách hình theo thứ tự ưu tiên cấu hình trong config.json:
    - Hình lớn trước (Diện tích thực / Diagonal / BBox Area)
    - Hình phức tạp trước (Isoperimetric complexity / Convexity ratio)
    - Hình dài trước (Aspect ratio / Bounding box height or width)
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def _get_sort_key(self, geom: NormalizedGeometry, key_name: str) -> float:
        key_name = key_name.lower()
        if key_name in ["area", "real_area"]:
            return geom.real_area
        elif key_name in ["complexity", "isoperimetric"]:
            return geom.isoperimetric_complexity
        elif key_name in ["aspect_ratio", "long"]:
            return geom.aspect_ratio
        elif key_name in ["diagonal"]:
            return geom.diagonal
        elif key_name in ["bbox_area"]:
            return geom.bbox_area
        elif key_name in ["convexity"]:
            return 1.0 - geom.convexity_ratio # More concave first
        return geom.real_area

    def sort(self, items: List[NormalizedGeometry]) -> List[NormalizedGeometry]:
        sort_cfg = self.config.sorting
        primary_k = sort_cfg.get("primary_key", "area")
        secondary_k = sort_cfg.get("secondary_key", "complexity")
        tertiary_k = sort_cfg.get("tertiary_key", "aspect_ratio")
        is_reverse = sort_cfg.get("reverse", True)

        def combined_key(geom: NormalizedGeometry):
            k1 = self._get_sort_key(geom, primary_k)
            k2 = self._get_sort_key(geom, secondary_k)
            k3 = self._get_sort_key(geom, tertiary_k)
            return (k1, k2, k3)

        sorted_list = sorted(items, key=combined_key, reverse=is_reverse)
        return sorted_list
