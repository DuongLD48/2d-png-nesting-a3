import numpy as np
from PIL import Image
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from typing import Dict, Any, Tuple, List, Union
from src.preprocessor import ItemImage

class NormalizedGeometry:
    """
    Dữ liệu hình học được chuẩn hóa chính xác theo kích thước ảnh PIL.
    Tự động xử lý MultiPolygon cho các file ảnh chứa nhiều đường viền rời rạc (chữ viết, sticker đa phần tử).
    """
    def __init__(self, item: ItemImage):
        self.item = item
        self.item_id = item.item_id
        self.orig_w = item.width
        self.orig_h = item.height
        self.contours_list = item.contours_list

        # Construct individual polygons for each separate contour
        poly_list = []
        for c_pts in item.contours_list:
            if len(c_pts) >= 3:
                p = Polygon(c_pts)
                if not p.is_valid:
                    p = p.buffer(0)
                if p.area > 0 and not p.is_empty:
                    poly_list.append(p)

        if not poly_list:
            # Fallback image box
            poly_list = [Polygon([(0, 0), (self.orig_w, 0), (self.orig_w, self.orig_h), (0, self.orig_h)])]

        # Combine into single geometry (Polygon or MultiPolygon)
        base_shape = unary_union(poly_list)
        if not base_shape.is_valid:
            base_shape = base_shape.buffer(0)
        self.shape = base_shape

        self.convex_hull = self.shape.convex_hull
        self.real_area = self.shape.area if self.shape.area > 0 else item.real_area
        self.hull_area = self.convex_hull.area if self.convex_hull.area > 0 else self.real_area
        self.bbox_area = float(self.orig_w * self.orig_h)

        # Complexity Metrics
        self.convexity_ratio = self.real_area / self.hull_area if self.hull_area > 0 else 1.0
        perimeter = self.shape.length
        self.isoperimetric_complexity = (perimeter ** 2) / self.real_area if self.real_area > 0 else 1.0
        self.aspect_ratio = max(self.orig_w, self.orig_h) / max(1.0, min(self.orig_w, self.orig_h))
        self.diagonal = np.sqrt(self.orig_w ** 2 + self.orig_h ** 2)

    def get_rotated_data(self, angle_deg: float) -> Tuple[Image.Image, Union[Polygon, MultiPolygon], float, float]:
        """
        Xoay ảnh PIL và biến đổi chính xác 100% tất cả các contours thành Polygon/MultiPolygon.
        Sử dụng Cache & PIL transpose siêu tốc cho các góc 90, 180, 270 độ.
        """
        if not hasattr(self, "_rotated_cache"):
            self._rotated_cache = {}

        norm_angle = float(angle_deg) % 360.0
        if norm_angle in self._rotated_cache:
            return self._rotated_cache[norm_angle]

        orig_pil = self.item.image_pil

        if norm_angle == 0:
            res = (orig_pil, self.shape, float(self.orig_w), float(self.orig_h))
            self._rotated_cache[0.0] = res
            return res

        # Ultra-fast loss-less C-transpose for orthogonal angles
        if norm_angle == 90:
            rot_pil = orig_pil.transpose(Image.Transpose.ROTATE_270)
        elif norm_angle == 180:
            rot_pil = orig_pil.transpose(Image.Transpose.ROTATE_180)
        elif norm_angle == 270:
            rot_pil = orig_pil.transpose(Image.Transpose.ROTATE_90)
        else:
            rot_pil = orig_pil.rotate(-norm_angle, resample=Image.Resampling.BILINEAR, expand=True)

        rot_w, rot_h = rot_pil.size

        # Exact transformation matrix corresponding to PIL rotate(expand=True)
        rad = np.radians(-norm_angle)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)

        cx_orig = self.orig_w / 2.0
        cy_orig = self.orig_h / 2.0
        cx_rot = rot_w / 2.0
        cy_rot = rot_h / 2.0

        rotated_polys = []

        for c_pts in self.contours_list:
            if len(c_pts) < 3:
                continue
            new_pts = []
            for x, y in c_pts:
                dx = x - cx_orig
                dy = y - cy_orig
                rx = dx * cos_a - dy * sin_a + cx_rot
                ry = dx * sin_a + dy * cos_a + cy_rot
                new_pts.append((rx, ry))

            p = Polygon(new_pts)
            if not p.is_valid:
                p = p.buffer(0)
            if p.area > 0 and not p.is_empty:
                rotated_polys.append(p)

        if not rotated_polys:
            rotated_polys = [Polygon([(0, 0), (rot_w, 0), (rot_w, rot_h), (0, rot_h)])]

        rot_shape = unary_union(rotated_polys)
        if not rot_shape.is_valid:
            rot_shape = rot_shape.buffer(0)

        res = (rot_pil, rot_shape, float(rot_w), float(rot_h))
        self._rotated_cache[norm_angle] = res
        return res
