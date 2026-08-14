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
        contours_list: List[np.ndarray], # Danh sách từng contour riêng biệt (không vstack)
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
        self.contours_list = contours_list
        self.bbox = bbox
        self.real_area = real_area
        self.bbox_area = bbox_area
        self.centroid = centroid
        self.perimeter = perimeter

class Preprocessor:
    """
    Tiền xử lý ảnh PNG:
    - Trích xuất từng Contour độc lập (Hỗ trợ hình gồm nhiều chữ cái/phần tử rời nhau)
    - Tự động scale nếu kích thước vượt A3 printable bounds
    - Tính Bounding Box, Diện tích thật, Centroid
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

        w_orig, h_orig = pil_img.size

        # Check embedded DPI / PPI metadata (e.g. Photoshop 500 DPI, 300 DPI)
        use_embedded_dpi = self.config.preprocessing.get("use_embedded_dpi", True)
        canvas_dpi = float(self.config.canvas.get("dpi", 150))
        
        embedded_dpi_info = pil_img.info.get("dpi")
        img_dpi = None
        if use_embedded_dpi and embedded_dpi_info and embedded_dpi_info[0] > 0:
            img_dpi = float(embedded_dpi_info[0])

        if img_dpi is not None and img_dpi > 0 and abs(img_dpi - canvas_dpi) > 1.0:
            # Convert pixels from embedded DPI (e.g. 300 DPI) to target canvas DPI
            w_mm = (w_orig / img_dpi) * 25.4
            h_mm = (h_orig / img_dpi) * 25.4
            
            target_w_px = max(1, int(round((w_mm * canvas_dpi) / 25.4)))
            target_h_px = max(1, int(round((h_mm * canvas_dpi) / 25.4)))
            
            if (target_w_px, target_h_px) != (w_orig, h_orig):
                # Fast BILINEAR resampling for speed
                pil_img = pil_img.resize((target_w_px, target_h_px), Image.Resampling.BILINEAR)
                print(f" -> [Auto DPI] File '{os.path.basename(file_path)}': Metadata {img_dpi:.0f} DPI -> Quy đổi về Canvas ({target_w_px}x{target_h_px} px @ {canvas_dpi:.0f} DPI)")

        # Check auto scaling for oversized images
        auto_scale = self.config.preprocessing.get("auto_scale_oversized", False)
        max_dim_mm = self.config.preprocessing.get("max_item_dimension_mm", 280.0)
        max_dim_px = self.config.mm_to_px(max_dim_mm)

        w_curr, h_curr = pil_img.size
        if auto_scale and (w_curr > max_dim_px or h_curr > max_dim_px):
            scale_factor = max_dim_px / float(max(w_curr, h_curr))
            new_w = max(10, int(w_curr * scale_factor))
            new_h = max(10, int(h_curr * scale_factor))
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)

        width, height = pil_img.size
        
        # Fast Alpha Channel extraction (1-channel uint8 instead of 4-channel RGBA)
        if "A" in pil_img.getbands():
            alpha_channel = np.array(pil_img.getchannel("A"))
        else:
            alpha_channel = np.full((height, width), 255, dtype=np.uint8)

        alpha_thresh_val = self.config.preprocessing.get("alpha_threshold", 10)

        # Ultra-fast downsampled contour extraction for large images (>1200px)
        scale_down = 1.0
        if max(width, height) > 1200:
            scale_down = max(width, height) / 1200.0
            ds_w = max(10, int(width / scale_down))
            ds_h = max(10, int(height / scale_down))
            ds_alpha = cv2.resize(alpha_channel, (ds_w, ds_h), interpolation=cv2.INTER_NEAREST)
            _, alpha_mask_ds = cv2.threshold(ds_alpha, alpha_thresh_val, 255, cv2.THRESH_BINARY)
            contours_raw, _ = cv2.findContours(alpha_mask_ds, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Scale contour coordinates back up to full size
            contours = []
            for c in contours_raw:
                scaled_c = (c.astype(np.float32) * scale_down).astype(np.int32)
                contours.append(scaled_c)
            
            _, alpha_mask = cv2.threshold(alpha_channel, alpha_thresh_val, 255, cv2.THRESH_BINARY)
        else:
            _, alpha_mask = cv2.threshold(alpha_channel, alpha_thresh_val, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(alpha_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            contours = [np.array([[[0, 0]], [[width, 0]], [[width, height]], [[0, height]]])]

        min_area = self.config.preprocessing.get("min_contour_area_px", 10.0)
        
        # Keep list of valid individual contours (do NOT vstack!)
        processed_contours = []
        total_real_area = 0.0
        total_perimeter = 0.0
        all_pts_for_bbox = []

        epsilon_ratio = self.config.preprocessing.get("contour_approx_epsilon", 0.003)

        for c in contours:
            c_area = cv2.contourArea(c)
            if c_area >= min_area:
                c_peri = cv2.arcLength(c, True)
                approx_c = cv2.approxPolyDP(c, max(1.0, epsilon_ratio * c_peri), True)
                if len(approx_c) >= 3:
                    pts_2d = approx_c.reshape(-1, 2)
                    processed_contours.append(pts_2d)
                    total_real_area += c_area
                    total_perimeter += c_peri
                    all_pts_for_bbox.append(pts_2d)

        # Fallback if no contour passed min_area filter
        if not processed_contours:
            for c in contours:
                pts_2d = c.reshape(-1, 2)
                if len(pts_2d) >= 3:
                    processed_contours.append(pts_2d)
                    total_real_area += cv2.contourArea(c)
                    all_pts_for_bbox.append(pts_2d)

        if not processed_contours:
            # Full image box fallback
            pts_2d = np.array([[0, 0], [width, 0], [width, height], [0, height]])
            processed_contours = [pts_2d]
            all_pts_for_bbox = [pts_2d]
            total_real_area = float(width * height)

        stacked_pts = np.vstack(all_pts_for_bbox)
        bx, by, bw, bh = cv2.boundingRect(stacked_pts)
        bbox = (int(bx), int(by), int(bw), int(bh))

        bbox_area = float(bw * bh)
        if total_real_area <= 0:
            total_real_area = bbox_area

        # Centroid / Center of mass
        M = cv2.moments(stacked_pts)
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
            contours_list=processed_contours,
            bbox=bbox,
            real_area=total_real_area,
            bbox_area=bbox_area,
            centroid=(cx, cy),
            perimeter=total_perimeter
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
        total_files = len(files)
        print(f" -> [BƯỚC 3/6] Đang tiền xử lý {total_files} file ảnh PNG...", flush=True)
        for idx, f in enumerate(sorted(files), start=1):
            fname = os.path.basename(f)
            print(f"    ↳ [{idx}/{total_files}] Đọc & tách viền kênh Alpha file '{fname}'...", flush=True)
            item = self.process_file(f)
            if item:
                items.append(item)
                print(f"    ✔ [{idx}/{total_files}] Hoàn tất '{fname}' (Contour polygons: {len(item.contours_list)})", flush=True)
        return items
