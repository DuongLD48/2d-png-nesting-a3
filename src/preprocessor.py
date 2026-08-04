import os
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional
from src.config_loader import ConfigLoader

# Disable PIL limit for large image files
Image.MAX_IMAGE_PIXELS = None

class ItemImage:
    """Class đại diện cho 1 ảnh PNG đầu vào đã qua xử lý hình học."""
    def __init__(
        self,
        item_id: str,
        file_path: str,
        image_pil: Image.Image,
        width: int,
        height: int,
        alpha_mask: np.ndarray,
        contour_pts: np.ndarray,
        bbox: Tuple[int, int, int, int],
        real_area: float,
        bbox_area: float,
        centroid: Tuple[float, float],
        perimeter: float
    ):
        self.item_id = item_id
        self.file_path = file_path
        self.image_pil = image_pil
        self.width = width
        self.height = height
        self.alpha_mask = alpha_mask
        self.contour_pts = contour_pts
        self.bbox = bbox
        self.real_area = real_area
        self.bbox_area = bbox_area
        self.centroid = centroid
        self.perimeter = perimeter

class Preprocessor:
    """
    Tiền xử lý ảnh PNG:
    - Đọc kích thước & Kênh Alpha
    - Tự động scale nếu kích thước vượt A3 printable bounds (theo config)
    - Tách Contour, Tính Bounding Box, Diện tích thật, Centroid
    """
    def __init__(self, config: ConfigLoader):
        self.config = config

    def process_file(self, file_path: str) -> Optional[ItemImage]:
        if not os.path.exists(file_path):
            return None

        try:
            pil_img = Image.open(file_path).convert("RGBA")
        except Exception as e:
            print(f"Lỗi khi đọc file ảnh {file_path}: {e}")
            return None

        # Check auto scaling for oversized images
        auto_scale = self.config.preprocessing.get("auto_scale_oversized", True)
        max_dim_mm = self.config.preprocessing.get("max_item_dimension_mm", 280.0)
        max_dim_px = self.config.mm_to_px(max_dim_mm)

        w_orig, h_orig = pil_img.size
        if auto_scale and (w_orig > max_dim_px or h_orig > max_dim_px):
            scale_factor = max_dim_px / float(max(w_orig, h_orig))
            new_w = max(10, int(w_orig * scale_factor))
            new_h = max(10, int(h_orig * scale_factor))
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BICUBIC)

        width, height = pil_img.size
        img_np = np.array(pil_img) # H x W x 4 (RGBA)
        alpha_channel = img_np[:, :, 3]

        alpha_thresh_val = self.config.preprocessing.get("alpha_threshold", 10)
        _, alpha_mask = cv2.threshold(alpha_channel, alpha_thresh_val, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(alpha_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            contours = [np.array([[[0, 0]], [[width, 0]], [[width, height]], [[0, height]]])]

        min_area = self.config.preprocessing.get("min_contour_area_px", 20.0)
        valid_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
        if not valid_contours:
            valid_contours = contours

        all_pts = np.vstack(valid_contours)
        
        # Simplify contour
        epsilon_ratio = self.config.preprocessing.get("contour_approx_epsilon", 0.003)
        perimeter = cv2.arcLength(all_pts, True)
        approx_contour = cv2.approxPolyDP(all_pts, epsilon_ratio * perimeter, True)
        if len(approx_contour) < 3:
            approx_contour = all_pts

        # Bounding box
        bx, by, bw, bh = cv2.boundingRect(all_pts)
        bbox = (int(bx), int(by), int(bw), int(bh))

        # Real Area & BBox Area
        real_area = float(sum(cv2.contourArea(c) for c in valid_contours))
        if real_area <= 0:
            real_area = float(bw * bh)
        bbox_area = float(bw * bh)

        # Centroid / Center of mass
        M = cv2.moments(all_pts)
        if M["m00"] != 0:
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
        else:
            cx = float(bx + bw / 2.0)
            cy = float(by + bh / 2.0)

        item_id = os.path.basename(file_path)

        return ItemImage(
            item_id=item_id,
            file_path=file_path,
            image_pil=pil_img,
            width=width,
            height=height,
            alpha_mask=alpha_mask,
            contour_pts=approx_contour,
            bbox=bbox,
            real_area=real_area,
            bbox_area=bbox_area,
            centroid=(cx, cy),
            perimeter=perimeter
        )

    def load_all_from_folder(self, folder_path: str) -> List[ItemImage]:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            return []

        files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(".png")
        ]
        
        items = []
        for f in sorted(files):
            item = self.process_file(f)
            if item:
                items.append(item)
        return items
