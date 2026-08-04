import numpy as np
from PIL import Image
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.affinity import translate
from typing import Dict, Any, Tuple
from src.preprocessor import ItemImage

class NormalizedGeometry:
    """
    Dữ liệu hình học được chuẩn hóa chính xác theo kích thước ảnh PIL.
    Đảm bảo khớp 100% giữa Polygon va chạm và ảnh Render khi xoay.
    """
    def __init__(self, item: ItemImage):
        self.item = item
        self.item_id = item.item_id

        # Convert contour points to 2D coordinates list
        pts = item.contour_pts.reshape(-1, 2)
        if len(pts) < 3:
            bx, by, bw, bh = item.bbox
            pts = np.array([[bx, by], [bx + bw, by], [bx + bw, by + bh], [bx, by + bh]])

        self.pts_orig = pts
        self.orig_w = item.width
        self.orig_h = item.height

        # Create base polygon in original image coordinates
        base_poly = Polygon(pts)
        if not base_poly.is_valid:
            base_poly = base_poly.buffer(0)
        self.polygon = base_poly

        self.convex_hull = self.polygon.convex_hull
        self.real_area = self.polygon.area if self.polygon.area > 0 else item.real_area
        self.hull_area = self.convex_hull.area if self.convex_hull.area > 0 else self.real_area
        self.bbox_area = float(self.orig_w * self.orig_h)

        # Complexity Metrics
        self.convexity_ratio = self.real_area / self.hull_area if self.hull_area > 0 else 1.0
        perimeter = self.polygon.length
        self.isoperimetric_complexity = (perimeter ** 2) / self.real_area if self.real_area > 0 else 1.0
        self.aspect_ratio = max(self.orig_w, self.orig_h) / max(1.0, min(self.orig_w, self.orig_h))
        self.diagonal = np.sqrt(self.orig_w ** 2 + self.orig_h ** 2)

    def get_rotated_data(self, angle_deg: float) -> Tuple[Image.Image, Polygon, float, float]:
        """
        Xoay ảnh PIL và biến đổi các tọa độ Polygon chuẩn xác theo ma trận xoay của PIL.
        Trả về (rot_pil_img, rot_polygon_at_origin, rot_img_width, rot_img_height)
        """
        orig_pil = self.item.image_pil

        if angle_deg == 0:
            rot_pil = orig_pil
            rot_poly = self.polygon
            return rot_pil, rot_poly, float(self.orig_w), float(self.orig_h)

        # PIL rotate angle is counter-clockwise.
        # Rotate with expand=True to get exact new image canvas dimensions
        rot_pil = orig_pil.rotate(-angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
        rot_w, rot_h = rot_pil.size

        # Exact transformation matrix corresponding to PIL rotate(expand=True)
        rad = np.radians(-angle_deg)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)

        cx_orig = self.orig_w / 2.0
        cy_orig = self.orig_h / 2.0
        cx_rot = rot_w / 2.0
        cy_rot = rot_h / 2.0

        new_pts = []
        for x, y in self.pts_orig:
            dx = x - cx_orig
            dy = y - cy_orig
            rx = dx * cos_a - dy * sin_a + cx_rot
            ry = dx * sin_a + dy * cos_a + cy_rot
            new_pts.append((rx, ry))

        rot_poly = Polygon(new_pts)
        if not rot_poly.is_valid:
            rot_poly = rot_poly.buffer(0)

        return rot_pil, rot_poly, float(rot_w), float(rot_h)
