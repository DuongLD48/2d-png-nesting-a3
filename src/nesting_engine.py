import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box
from shapely.affinity import translate
from shapely.strtree import STRtree
from typing import List, Dict, Any, Tuple, Optional
from src.config_loader import ConfigLoader
from src.geometry import NormalizedGeometry

class PlacedItem:
    """Đại diện cho 1 đối tượng đã được xếp lên trang A3."""
    def __init__(
        self,
        sheet_index: int,
        geom: NormalizedGeometry,
        x: float,
        y: float,
        rotation_deg: float,
        rot_pil: Image.Image,
        placed_polygon: Polygon,
        placed_buffered_polygon: Polygon,
        rot_w: float,
        rot_h: float
    ):
        self.sheet_index = sheet_index
        self.geom = geom
        self.item_id = geom.item_id
        self.x = x
        self.y = y
        self.rotation_deg = rotation_deg
        self.rot_pil = rot_pil
        self.placed_polygon = placed_polygon
        self.placed_buffered_polygon = placed_buffered_polygon
        self.rot_w = rot_w
        self.rot_h = rot_h

class A3Sheet:
    """Đại diện cho 1 trang A3 chứa danh sách các vật thể được xếp."""
    def __init__(self, sheet_index: int, config: ConfigLoader):
        self.sheet_index = sheet_index
        self.config = config
        
        self.width_px = config.canvas_width_px
        self.height_px = config.canvas_height_px
        
        min_x, min_y, max_x, max_y = config.printable_bounds_px
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        
        self.placed_items: List[PlacedItem] = []
        self.placed_buffered_polygons: List[Polygon] = []
        self.spatial_tree: Optional[STRtree] = None

    def _rebuild_tree(self):
        if self.placed_buffered_polygons:
            self.spatial_tree = STRtree(self.placed_buffered_polygons)
        else:
            self.spatial_tree = None

    def can_place(
        self,
        x: float,
        y: float,
        rot_w: float,
        rot_h: float,
        candidate_buffered_poly: Polygon,
        candidate_poly: Polygon
    ) -> bool:
        # STRICT BOUNDARY CHECK: Entire Image Box MUST fit 100% inside printable bounds
        if x < self.min_x or y < self.min_y or (x + rot_w) > self.max_x or (y + rot_h) > self.max_y:
            return False

        if not self.placed_buffered_polygons:
            return True

        # Fast R-Tree spatial index query for Polygon collision
        if self.spatial_tree is not None:
            possible_matches = self.spatial_tree.query(candidate_buffered_poly)
            for idx in possible_matches:
                existing_poly = self.placed_buffered_polygons[idx]
                if candidate_buffered_poly.intersects(existing_poly):
                    return False
        else:
            for existing_poly in self.placed_buffered_polygons:
                if candidate_buffered_poly.intersects(existing_poly):
                    return False

        return True

    def place_item(
        self,
        geom: NormalizedGeometry,
        x: float,
        y: float,
        rotation_deg: float,
        rot_pil: Image.Image,
        rot_poly: Polygon,
        rot_w: float,
        rot_h: float,
        padding_px: float
    ) -> PlacedItem:
        placed_poly = translate(rot_poly, xoff=x, yoff=y)
        
        pad_buffer = padding_px / 2.0 if padding_px > 0 else 0.001
        placed_buf_poly = placed_poly.buffer(pad_buffer)

        placed_obj = PlacedItem(
            sheet_index=self.sheet_index,
            geom=geom,
            x=x,
            y=y,
            rotation_deg=rotation_deg,
            rot_pil=rot_pil,
            placed_polygon=placed_poly,
            placed_buffered_polygon=placed_buf_poly,
            rot_w=rot_w,
            rot_h=rot_h
        )

        self.placed_items.append(placed_obj)
        self.placed_buffered_polygons.append(placed_buf_poly)
        self._rebuild_tree()
        return placed_obj


class NestingEngine:
    """
    Nesting Engine thực hiện:
    - Xoay hình học theo danh sách góc cấu hình
    - Collision Detection với R-Tree Spatial Index
    - Nghiêm cấm hoàn toàn hành vi tràn khung A3
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def nest_all(self, sorted_geoms: List[NormalizedGeometry]) -> List[A3Sheet]:
        sheets: List[A3Sheet] = []
        current_sheet = A3Sheet(sheet_index=1, config=self.config)
        sheets.append(current_sheet)

        rotation_angles = self.config.nesting.get("rotation_angles_deg", [0, 90, 180, 270])
        padding_px = self.config.padding_px
        search_step_px = max(5, int(self.config.nesting.get("search_step_px", 10)))
        max_sheets_limit = self.config.nesting.get("max_sheets_limit", 50)

        for idx, geom in enumerate(sorted_geoms, start=1):
            placed = False

            # Pre-compute rotated PIL images, polygons, and exact bounding sizes
            rotations_data = []
            for angle in rotation_angles:
                rot_pil, rot_poly, rot_w, rot_h = geom.get_rotated_data(angle)
                pad_buffer = padding_px / 2.0 if padding_px > 0 else 0.001
                rot_buf_poly = rot_poly.buffer(pad_buffer)
                rotations_data.append((angle, rot_pil, rot_poly, rot_buf_poly, rot_w, rot_h))

            # Try placing in existing sheets
            for sheet in sheets:
                best_pos = self._find_best_position(sheet, rotations_data, search_step_px)
                if best_pos is not None:
                    x, y, angle, rot_pil, rot_poly, rot_w, rot_h = best_pos
                    sheet.place_item(geom, x, y, angle, rot_pil, rot_poly, rot_w, rot_h, padding_px)
                    placed = True
                    break

            # If not placed, spawn new A3 sheet
            if not placed:
                while len(sheets) < max_sheets_limit and not placed:
                    new_sheet = A3Sheet(sheet_index=len(sheets) + 1, config=self.config)
                    best_pos = self._find_best_position(new_sheet, rotations_data, search_step_px)
                    if best_pos is not None:
                        x, y, angle, rot_pil, rot_poly, rot_w, rot_h = best_pos
                        new_sheet.place_item(geom, x, y, angle, rot_pil, rot_poly, rot_w, rot_h, padding_px)
                        sheets.append(new_sheet)
                        placed = True
                        break
                    else:
                        print(f"Cảnh báo: Vật thể {geom.item_id} quá lớn so với trang A3!")
                        break

        return sheets

    def _find_best_position(
        self,
        sheet: A3Sheet,
        rotations_data: List[Tuple[float, Image.Image, Polygon, Polygon, float, float]],
        search_step_px: int
    ) -> Optional[Tuple[float, float, float, Image.Image, Polygon, float, float]]:
        best_candidate = None
        min_score = float('inf')

        min_x, min_y, max_x, max_y = sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y
        padding_px = sheet.config.padding_px

        # Generate candidate anchor points from corners of already placed items + margins
        candidate_points = [(min_x, min_y)]

        for item in sheet.placed_items:
            candidate_points.append((item.x + item.rot_w + padding_px, min_y))
            candidate_points.append((item.x + item.rot_w + padding_px, item.y))
            candidate_points.append((min_x, item.y + item.rot_h + padding_px))
            candidate_points.append((item.x, item.y + item.rot_h + padding_px))
            candidate_points.append((item.x + item.rot_w + padding_px, item.y + item.rot_h + padding_px))

        # Add x-strip and y-strip anchor points from items
        x_anchors = sorted(list(set([min_x] + [it.x for it in sheet.placed_items] + [it.x + it.rot_w + padding_px for it in sheet.placed_items])))
        y_anchors = sorted(list(set([min_y] + [it.y for it in sheet.placed_items] + [it.y + it.rot_h + padding_px for it in sheet.placed_items])))

        for xa in x_anchors:
            for ya in y_anchors:
                candidate_points.append((xa, ya))

        # Filter points that fit within printable bounds
        unique_pts = []
        seen = set()
        for px, py in candidate_points:
            rpx, rpy = round(px, 1), round(py, 1)
            if (rpx, rpy) not in seen and min_x <= px <= max_x and min_y <= py <= max_y:
                seen.add((rpx, rpy))
                unique_pts.append((px, py))

        # Sort candidate points by Bottom-Left score (y primary, x secondary)
        unique_pts.sort(key=lambda pt: (pt[1], pt[0]))

        for angle, rot_pil, rot_poly, rot_buf_poly, rot_w, rot_h in rotations_data:
            if rot_w > (max_x - min_x) or rot_h > (max_y - min_y):
                continue

            for x, y in unique_pts:
                if (x + rot_w) > max_x or (y + rot_h) > max_y:
                    continue

                score = y * 100000.0 + x
                if score >= min_score:
                    continue

                cand_poly = translate(rot_poly, xoff=x, yoff=y)
                cand_buf_poly = translate(rot_buf_poly, xoff=x, yoff=y)

                if sheet.can_place(x, y, rot_w, rot_h, cand_buf_poly, cand_poly):
                    min_score = score
                    best_candidate = (float(x), float(y), angle, rot_pil, rot_poly, rot_w, rot_h)

        return best_candidate
