from shapely.geometry import Polygon
from typing import List, Dict, Any, Tuple
from src.config_loader import ConfigLoader
from src.nesting_engine import A3Sheet, PlacedItem

class QualityCheckResult:
    def __init__(self, is_valid: bool, issues: List[str], stats: Dict[str, Any]):
        self.is_valid = is_valid
        self.issues = issues
        self.stats = stats

class QualityChecker:
    """
    Quality Check Engine:
    - Kiểm tra Overlap (chồng hình)
    - Kiểm tra Out of Bounds (vượt biên A3 cả Polygon lẫn Bounding Box ảnh)
    - Kiểm tra Padding đủ khoảng cách
    - Đánh giá tính hợp lệ tổng thể
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def validate_sheet(self, sheet: A3Sheet) -> QualityCheckResult:
        issues: List[str] = []
        allow_overlap = self.config.quality_check.get("allow_overlap", False)
        enforce_margins = self.config.quality_check.get("enforce_margins", True)
        enforce_padding = self.config.quality_check.get("enforce_padding", True)
        tolerance = self.config.quality_check.get("tolerance_px", 0.5)

        min_x, min_y, max_x, max_y = sheet.config.printable_bounds_px
        items = sheet.placed_items

        # 1. Strict Out of bounds check: Image box & Polygon
        if enforce_margins:
            for item in items:
                img_x1 = item.x
                img_y1 = item.y
                img_x2 = item.x + item.rot_w
                img_y2 = item.y + item.rot_h

                if (img_x1 < min_x - tolerance or
                    img_y1 < min_y - tolerance or
                    img_x2 > max_x + tolerance or
                    img_y2 > max_y + tolerance):
                    issues.append(
                        f"Vật thể '{item.item_id}' trang A3_{sheet.sheet_index:03d} tràn khung A3! "
                        f"Khung ảnh: ({img_x1:.1f}, {img_y1:.1f}, {img_x2:.1f}, {img_y2:.1f}) vs A3 Bounds ({min_x}, {min_y}, {max_x}, {max_y})"
                    )

        # 2. Overlap & Padding check
        padding_target_px = sheet.config.padding_px

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a = items[i]
                item_b = items[j]

                poly_a = item_a.placed_polygon
                poly_b = item_b.placed_polygon

                # Overlap check
                if not allow_overlap and poly_a.intersects(poly_b):
                    intersection_area = poly_a.intersection(poly_b).area
                    if intersection_area > tolerance:
                        issues.append(
                            f"Phát hiện đè hình giữa '{item_a.item_id}' và '{item_b.item_id}' "
                            f"trên trang A3_{sheet.sheet_index:03d}! Diện tích đè: {intersection_area:.2f}px²"
                        )

                # Distance / Padding check
                if enforce_padding and padding_target_px > 0:
                    dist = poly_a.distance(poly_b)
                    if dist < (padding_target_px - tolerance):
                        issues.append(
                            f"Cảnh báo Padding không đủ giữa '{item_a.item_id}' và '{item_b.item_id}' "
                            f"trên trang A3_{sheet.sheet_index:03d}: {dist:.2f}px vs Yêu cầu {padding_target_px:.2f}px"
                        )

        # Compute efficiency stats
        total_sheet_area = sheet.width_px * sheet.height_px
        printable_area = (max_x - min_x) * (max_y - min_y)
        used_items_area = sum(item.geom.real_area for item in items)
        
        waste_area = printable_area - used_items_area
        efficiency_pct = (used_items_area / printable_area * 100.0) if printable_area > 0 else 0.0

        stats = {
            "sheet_index": sheet.sheet_index,
            "total_items": len(items),
            "used_area_px": used_items_area,
            "printable_area_px": printable_area,
            "waste_area_px": waste_area,
            "efficiency_percent": round(efficiency_pct, 2)
        }

        is_valid = (len(issues) == 0)
        return QualityCheckResult(is_valid=is_valid, issues=issues, stats=stats)

    def validate_all(self, sheets: List[A3Sheet]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        all_issues = []
        all_stats = []
        overall_valid = True

        for sheet in sheets:
            res = self.validate_sheet(sheet)
            if not res.is_valid:
                overall_valid = False
            all_issues.extend(res.issues)
            all_stats.append(res.stats)

        return overall_valid, all_issues, all_stats
