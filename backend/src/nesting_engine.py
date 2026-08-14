import numpy as np
from PIL import Image
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import translate
from shapely.strtree import STRtree
from typing import List, Dict, Any, Tuple, Optional, Union
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
        placed_polygon: Union[Polygon, MultiPolygon],
        placed_buffered_polygon: Union[Polygon, MultiPolygon],
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
        self.placed_buffered_polygons: List[Union[Polygon, MultiPolygon]] = []
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
        candidate_buffered_poly: Union[Polygon, MultiPolygon],
        candidate_poly: Union[Polygon, MultiPolygon]
    ) -> bool:
        # STRICT BOUNDARY CHECK WITH SUB-PIXEL TOLERANCE
        tolerance = float(self.config.quality_check.get("tolerance_px", 1.0))
        if x < (self.min_x - tolerance) or y < (self.min_y - tolerance) or (x + rot_w) > (self.max_x + tolerance) or (y + rot_h) > (self.max_y + tolerance):
            return False

        if not self.placed_buffered_polygons:
            return True

        # Fast R-Tree spatial index query for Polygon/MultiPolygon collision
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
        rot_poly: Union[Polygon, MultiPolygon],
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

    def pop_item(self) -> Optional[PlacedItem]:
        if self.placed_items:
            popped = self.placed_items.pop()
            self.placed_buffered_polygons.pop()
            self._rebuild_tree()
            return popped
        return None

    def clear(self):
        self.placed_items.clear()
        self.placed_buffered_polygons.clear()
        self.spatial_tree = None


class NestingEngine:
    """
    Nesting Engine nâng cấp:
    - Giữ nguyên 100% kích thước ảnh gốc (Không auto-scale làm méo/sai size)
    - Tự động bỏ qua file vượt quá khổ giấy (hiện cảnh báo Console Log rõ ràng)
    - Xoay tự do 360 độ (theo góc step cấu hình trong config.json)
    - Re-Packing DFS siêu tốc tự xoay dọc/ngang các hình để vừa 1 khổ thay vì tách nhiều trang
    - Nghiêm cấm hoàn toàn chồng đè và tràn khung giấy
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def nest_all(self, sorted_geoms: List[NormalizedGeometry]) -> List[A3Sheet]:
        sheets: List[A3Sheet] = []
        current_sheet = A3Sheet(sheet_index=1, config=self.config)
        sheets.append(current_sheet)

        rotation_angles = self.config.rotation_angles
        padding_px = self.config.padding_px
        search_step_px = max(5, int(self.config.nesting.get("search_step_px", 10)))
        max_sheets_limit = self.config.nesting.get("max_sheets_limit", 50)
        tolerance = float(self.config.quality_check.get("tolerance_px", 1.0))

        printable_w = current_sheet.max_x - current_sheet.min_x
        printable_h = current_sheet.max_y - current_sheet.min_y

        # Pre-filter geoms: Skip oversized files that cannot fit in ANY orientation on an empty sheet
        valid_geoms: List[NormalizedGeometry] = []
        for geom in sorted_geoms:
            can_fit = False
            for angle in rotation_angles:
                _, _, rot_w, rot_h = geom.get_rotated_data(angle)
                if rot_w <= (printable_w + tolerance) and rot_h <= (printable_h + tolerance):
                    can_fit = True
                    break

            if not can_fit:
                w_mm = self.config.px_to_mm(geom.orig_w)
                h_mm = self.config.px_to_mm(geom.orig_h)
                p_w_mm = self.config.px_to_mm(printable_w)
                p_h_mm = self.config.px_to_mm(printable_h)
                print(f"[CẢNH BÁO OVERSIZE] File '{geom.item_id}' kích thước ({w_mm:.1f}x{h_mm:.1f} mm) lớn hơn vùng in khổ giấy ({p_w_mm:.1f}x{p_h_mm:.1f} mm). ĐÃ BỎ QUA FILE NÀY để tránh tốn giấy & sai kích thước gốc!")
            else:
                valid_geoms.append(geom)

        total_valid = len(valid_geoms)
        print(f" -> [BƯỚC 5/6] Bắt đầu Nesting Engine 2D cho {total_valid} hình vẽ...", flush=True)

        for idx, geom in enumerate(valid_geoms, start=1):
            placed = False
            print(f"    ↳ [{idx}/{total_valid}] Đang tính toán góc xoay & vị trí tốt nhất cho '{geom.item_id}'...", flush=True)

            # Pre-compute rotated PIL images, polygons, and exact bounding sizes for candidate
            rotations_data = []
            for angle in rotation_angles:
                rot_pil, rot_poly, rot_w, rot_h = geom.get_rotated_data(angle)
                pad_buffer = padding_px / 2.0 if padding_px > 0 else 0.001
                rot_buf_poly = rot_poly.buffer(pad_buffer)
                rotations_data.append((angle, rot_pil, rot_poly, rot_buf_poly, rot_w, rot_h))

            # 1. Try placing in existing sheets with direct placement
            for sheet in sheets:
                best_pos = self._find_best_position(sheet, rotations_data, search_step_px)
                if best_pos is not None:
                    x, y, angle, rot_pil, rot_poly, rot_w, rot_h = best_pos
                    sheet.place_item(geom, x, y, angle, rot_pil, rot_poly, rot_w, rot_h, padding_px)
                    placed = True
                    print(f"    ✔ [{idx}/{total_valid}] Đã xếp '{geom.item_id}' vào Trang {sheet.sheet_index} tại góc {angle}°", flush=True)
                    break

            # 2. If direct placement failed on existing sheets, try DFS Re-Packing Optimization on existing sheets!
            if not placed:
                for sheet in sheets:
                    existing_geoms = [item.geom for item in sheet.placed_items]
                    candidate_group = existing_geoms + [geom]
                    
                    repacked_sheet = self._try_repack_dfs(sheet.sheet_index, candidate_group, rotation_angles, padding_px, search_step_px)
                    if repacked_sheet is not None:
                        sheet.clear()
                        for p_item in repacked_sheet.placed_items:
                            sheet.place_item(
                                p_item.geom, p_item.x, p_item.y, p_item.rotation_deg,
                                p_item.rot_pil, p_item.placed_polygon, p_item.rot_w, p_item.rot_h, padding_px
                            )
                        placed = True
                        print(f"    ✔ [{idx}/{total_valid}] Re-Packing DFS: Đã dồn xếp '{geom.item_id}' vừa vào Trang {sheet.sheet_index}!", flush=True)
                        break

            # 3. If still not placed, spawn new sheet
            if not placed:
                while len(sheets) < max_sheets_limit and not placed:
                    new_sheet = A3Sheet(sheet_index=len(sheets) + 1, config=self.config)
                    best_pos = self._find_best_position(new_sheet, rotations_data, search_step_px)
                    if best_pos is not None:
                        x, y, angle, rot_pil, rot_poly, rot_w, rot_h = best_pos
                        new_sheet.place_item(geom, x, y, angle, rot_pil, rot_poly, rot_w, rot_h, padding_px)
                        sheets.append(new_sheet)
                        placed = True
                        print(f"    ✔ [{idx}/{total_valid}] Mở Trang Mới {new_sheet.sheet_index} & xếp '{geom.item_id}' thành công!", flush=True)
                        break
                    else:
                        print(f"Cảnh báo: Không thể xếp {geom.item_id} vào trang mới!", flush=True)
                        break

        for sheet in sheets:
            self._center_sheet_layout(sheet)

        return sheets


    def _center_sheet_layout(self, sheet: A3Sheet):
        """
        Căn giữa toàn bộ bố cục các hình đã xếp trên tờ giấy (Canvas),
        đảm bảo khoảng cách cách đều 4 mép Trên / Dưới / Trái / Phải.
        """
        if not sheet.placed_items:
            return

        center_layout = self.config.nesting.get("center_layout", True)
        if not center_layout:
            return

        center_in_printable = self.config.nesting.get("center_in_printable_area", True)

        placed_min_x = min(item.x for item in sheet.placed_items)
        placed_max_x = max(item.x + item.rot_w for item in sheet.placed_items)
        placed_min_y = min(item.y for item in sheet.placed_items)
        placed_max_y = max(item.y + item.rot_h for item in sheet.placed_items)

        content_w = placed_max_x - placed_min_x
        content_h = placed_max_y - placed_min_y

        if center_in_printable:
            target_min_x = sheet.min_x + (sheet.max_x - sheet.min_x - content_w) / 2.0
            target_min_y = sheet.min_y + (sheet.max_y - sheet.min_y - content_h) / 2.0
        else:
            target_min_x = (sheet.width_px - content_w) / 2.0
            target_min_y = (sheet.height_px - content_h) / 2.0

        shift_x = target_min_x - placed_min_x
        shift_y = target_min_y - placed_min_y

        if abs(shift_x) < 0.01 and abs(shift_y) < 0.01:
            return

        for item in sheet.placed_items:
            item.x += shift_x
            item.y += shift_y
            item.placed_polygon = translate(item.placed_polygon, xoff=shift_x, yoff=shift_y)
            item.placed_buffered_polygon = translate(item.placed_buffered_polygon, xoff=shift_x, yoff=shift_y)

        sheet._rebuild_tree()


    def _try_repack_dfs(
        self,
        sheet_index: int,
        group_geoms: List[NormalizedGeometry],
        rotation_angles: List[float],
        padding_px: float,
        search_step_px: int
    ) -> Optional[A3Sheet]:
        """
        Thử xếp lại nhóm vật thể bằng thuật toán DFS Backtracking.
        Tự động thử mọi kết hợp góc xoay hợp lệ để dồn tối đa các hình vào 1 trang duy nhất.
        """
        test_sheet = A3Sheet(sheet_index=sheet_index, config=self.config)
        sheet_printable_area = (test_sheet.max_x - test_sheet.min_x) * (test_sheet.max_y - test_sheet.min_y)
        total_group_area = sum(g.real_area for g in group_geoms)
        if total_group_area > sheet_printable_area * 0.90:
            return None

        sorted_group = sorted(group_geoms, key=lambda g: g.real_area, reverse=True)

        # For repacking efficiency, use principal angles [0, 90, 180, 270] if group is large
        repack_angles = rotation_angles
        if len(sorted_group) > 3:
            repack_angles = [a for a in rotation_angles if int(a) in [0, 90, 180, 270]]
            if not repack_angles:
                repack_angles = rotation_angles[:4]

        max_states = 40
        state_count = 0

        def dfs_pack(item_idx: int) -> bool:
            nonlocal state_count
            state_count += 1
            if state_count > max_states:
                return False

            if item_idx >= len(sorted_group):
                return True

            geom = sorted_group[item_idx]
            rotations_data = []
            for angle in repack_angles:
                rot_pil, rot_poly, rot_w, rot_h = geom.get_rotated_data(angle)
                pad_buffer = padding_px / 2.0 if padding_px > 0 else 0.001
                rot_buf_poly = rot_poly.buffer(pad_buffer)
                rotations_data.append((angle, rot_pil, rot_poly, rot_buf_poly, rot_w, rot_h))

            candidates = self._find_all_candidates(test_sheet, rotations_data, search_step_px)
            for x, y, angle, rot_pil, rot_poly, rot_w, rot_h in candidates[:4]:
                test_sheet.place_item(geom, x, y, angle, rot_pil, rot_poly, rot_w, rot_h, padding_px)
                if dfs_pack(item_idx + 1):
                    return True
                test_sheet.pop_item()

            return False

        if dfs_pack(0):
            return test_sheet
        return None

    def _find_all_candidates(
        self,
        sheet: A3Sheet,
        rotations_data: List[Tuple[float, Image.Image, Union[Polygon, MultiPolygon], Union[Polygon, MultiPolygon], float, float]],
        search_step_px: int
    ) -> List[Tuple[float, float, float, Image.Image, Union[Polygon, MultiPolygon], float, float]]:
        min_x, min_y, max_x, max_y = sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y
        padding_px = sheet.config.padding_px

        candidate_points = [(min_x, min_y)]

        for item in sheet.placed_items:
            candidate_points.append((item.x + item.rot_w + padding_px, min_y))
            candidate_points.append((item.x + item.rot_w + padding_px, item.y))
            candidate_points.append((min_x, item.y + item.rot_h + padding_px))
            candidate_points.append((item.x, item.y + item.rot_h + padding_px))
            candidate_points.append((item.x + item.rot_w + padding_px, item.y + item.rot_h + padding_px))

        x_anchors = sorted(list(set([min_x] + [it.x for it in sheet.placed_items] + [it.x + it.rot_w + padding_px for it in sheet.placed_items])))
        y_anchors = sorted(list(set([min_y] + [it.y for it in sheet.placed_items] + [it.y + it.rot_h + padding_px for it in sheet.placed_items])))

        for xa in x_anchors:
            for ya in y_anchors:
                candidate_points.append((xa, ya))

        unique_pts = []
        seen = set()
        for px, py in candidate_points:
            rpx, rpy = round(px, 1), round(py, 1)
            if (rpx, rpy) not in seen and min_x <= px <= max_x and min_y <= py <= max_y:
                seen.add((rpx, rpy))
                unique_pts.append((px, py))

        unique_pts.sort(key=lambda pt: (pt[1], pt[0]))

        valid_candidates = []
        tolerance = float(sheet.config.quality_check.get("tolerance_px", 1.0))
        for angle, rot_pil, rot_poly, rot_buf_poly, rot_w, rot_h in rotations_data:
            if rot_w > (max_x - min_x + tolerance) or rot_h > (max_y - min_y + tolerance):
                continue

            for x, y in unique_pts:
                if (x + rot_w) > (max_x + tolerance) or (y + rot_h) > (max_y + tolerance):
                    continue

                cand_poly = translate(rot_poly, xoff=x, yoff=y)
                cand_buf_poly = translate(rot_buf_poly, xoff=x, yoff=y)

                if sheet.can_place(x, y, rot_w, rot_h, cand_buf_poly, cand_poly):
                    valid_candidates.append((float(x), float(y), angle, rot_pil, rot_poly, rot_w, rot_h))

        return valid_candidates

    def _find_best_position(
        self,
        sheet: A3Sheet,
        rotations_data: List[Tuple[float, Image.Image, Union[Polygon, MultiPolygon], Union[Polygon, MultiPolygon], float, float]],
        search_step_px: int
    ) -> Optional[Tuple[float, float, float, Image.Image, Union[Polygon, MultiPolygon], float, float]]:
        candidates = self._find_all_candidates(sheet, rotations_data, search_step_px)
        if not candidates:
            return None

        min_x, min_y, max_x, max_y = sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y
        best_candidate = None
        min_score = float('inf')

        for x, y, angle, rot_pil, rot_poly, rot_w, rot_h in candidates:
            cur_max_x = max([it.x + it.rot_w for it in sheet.placed_items] + [x + rot_w])
            cur_max_y = max([it.y + it.rot_h for it in sheet.placed_items] + [y + rot_h])
            
            rem_w = max_x - cur_max_x
            rem_h = max_y - cur_max_y
            usable_rem = max(rem_w, rem_h)

            occupied_area = (cur_max_x - min_x) * (cur_max_y - min_y)
            score = occupied_area * 1000.0 - usable_rem * 500.0 + y * 10.0 + x

            if score < min_score:
                min_score = score
                best_candidate = (x, y, angle, rot_pil, rot_poly, rot_w, rot_h)

        return best_candidate
