import os
import json
import pandas as pd
from typing import List, Dict, Any
from src.config_loader import ConfigLoader
from src.nesting_engine import A3Sheet

class Exporter:
    """
    Exporter Engine:
    - Ghi file layout.json chi tiết vị trí từng hình, góc xoay, số trang A3
    - Ghi file report.csv thống kê hiệu suất sử dụng diện tích A3
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def export_layout_json(self, sheets: List[A3Sheet], output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        json_filename = self.config.paths.get("layout_filename", "layout.json")
        json_path = os.path.join(output_dir, json_filename)

        layout_data = {
            "config": self.config.raw_config,
            "canvas_px": {
                "width": self.config.canvas_width_px,
                "height": self.config.canvas_height_px,
                "printable_bounds": list(self.config.printable_bounds_px)
            },
            "total_sheets": len(sheets),
            "sheets": []
        }

        for sheet in sheets:
            sheet_info = {
                "sheet_index": sheet.sheet_index,
                "items_count": len(sheet.placed_items),
                "items": []
            }

            for item in sheet.placed_items:
                poly = item.placed_polygon
                if hasattr(poly, 'exterior'):
                    poly_coords = [list(p) for p in list(poly.exterior.coords)]
                elif hasattr(poly, 'geoms'):
                    poly_coords = [list(p) for g in poly.geoms for p in list(g.exterior.coords)]

                else:
                    poly_coords = []

                sheet_info["items"].append({
                    "item_id": item.item_id,
                    "file_path": item.geom.item.file_path,
                    "position_px": {
                        "x": round(item.x, 2),
                        "y": round(item.y, 2)
                    },
                    "rotation_deg": item.rotation_deg,
                    "dimensions_px": {
                        "width": round(item.rot_w, 2),
                        "height": round(item.rot_h, 2)
                    },
                    "real_area_px2": round(item.geom.real_area, 2),
                    "polygon_coords": poly_coords
                })


            layout_data["sheets"].append(sheet_info)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout_data, f, ensure_ascii=False, indent=2)

        print(f"Đã xuất file dữ liệu layout: {json_path}")
        return json_path

    def export_report_csv(self, stats: List[Dict[str, Any]], output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = self.config.paths.get("report_filename", "report.csv")
        csv_path = os.path.join(output_dir, csv_filename)

        df = pd.DataFrame(stats)
        
        # Add summary row
        if not df.empty:
            total_items = df["total_items"].sum()
            total_used_area = df["used_area_px"].sum()
            total_printable_area = df["printable_area_px"].sum()
            total_waste = df["waste_area_px"].sum()
            overall_eff = round((total_used_area / total_printable_area * 100.0), 2) if total_printable_area > 0 else 0.0

            summary_row = pd.DataFrame([{
                "sheet_index": "TOTAL / AVG",
                "total_items": total_items,
                "used_area_px": total_used_area,
                "printable_area_px": total_printable_area,
                "waste_area_px": total_waste,
                "efficiency_percent": overall_eff
            }])

            df = pd.concat([df, summary_row], ignore_index=True)

        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"Đã xuất file báo cáo thống kê CSV: {csv_path}")
        return csv_path
