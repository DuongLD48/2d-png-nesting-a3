import os
import re
import shutil
import glob
import logging

logger = logging.getLogger("sku_processor")

def parse_sku(sku_str):
    """
    Parses SKU formatted as [ID]-[ÁO]-[SIZE] (e.g., '03-D-XL', '01-T-M', '105-W-L')
    Returns dict: {'id': '03', 'color': 'D', 'size': 'XL'} or None if unparseable
    """
    if not sku_str or not isinstance(sku_str, str):
        return None
    
    sku_str = sku_str.strip()
    
    # Standard pattern: [ID]-[COLOR]-[SIZE] (e.g. 03-D-XL, 1-T-M, 105-W-L)
    match = re.match(r"^(\d+)-([A-Za-z]+)-(.*)$", sku_str)
    if match:
        raw_id, color, size = match.groups()
        # Preserve original string id or format with two digits if 1 digit
        item_id = raw_id.zfill(2) if len(raw_id) == 1 else raw_id
        return {
            "id": item_id,
            "color": color.upper(),
            "size": size.upper(),
            "raw_id": raw_id
        }
    
    # Fallback pattern for numeric prefix e.g. '03_D_XL' or '03-D'
    parts = re.split(r"[-_]", sku_str)
    if len(parts) >= 2 and parts[0].isdigit():
        raw_id = parts[0]
        item_id = raw_id.zfill(2) if len(raw_id) == 1 else raw_id
        return {
            "id": item_id,
            "color": parts[1].upper(),
            "size": parts[2].upper() if len(parts) > 2 else "FREE",
            "raw_id": raw_id
        }

    return None

def find_matching_images(sku_info, anhlocal_dir):
    """
    Finds image files in anhlocal_dir based on SKU color rules:
    - Shirt color in ['T', 'B'] -> copy files containing 'SANG'
    - Shirt color in ['D', 'W', 'X'] -> copy files containing 'TOI'
    """
    if not sku_info or not os.path.exists(anhlocal_dir):
        return []

    item_id = sku_info["id"]
    raw_id = sku_info["raw_id"]
    color = sku_info["color"]

    # Rule 1: Light colors ('T', 'B') -> 'SANG', Dark colors ('D', 'W', 'X') -> 'TOI'
    light_colors = {"T", "B"}
    dark_colors = {"D", "W", "X"}

    target_kw = None
    if color in light_colors:
        target_kw = "SANG"
    elif color in dark_colors:
        target_kw = "TOI"

    matched_files = []

    # Search candidates: Subdirectories in ANHLOCAL starting with item_id or raw_id
    subdirs = []
    try:
        for entry in os.scandir(anhlocal_dir):
            if entry.is_dir():
                name = entry.name
                if name.startswith(f"{item_id}-") or name.startswith(f"{raw_id}-") or name == item_id or name == raw_id:
                    subdirs.append(entry.path)
    except Exception as e:
        logger.error(f"Error scanning anhlocal_dir {anhlocal_dir}: {e}")

    # Also search directly in root anhlocal_dir
    search_dirs = subdirs if subdirs else [anhlocal_dir]

    for sdir in search_dirs:
        for root, _, files in os.walk(sdir):
            for file in files:
                if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue

                # Check if file belongs to item_id
                upper_file = file.upper()
                is_id_match = (
                    upper_file.startswith(f"{item_id}-") or 
                    upper_file.startswith(f"{raw_id}-") or 
                    f"-{item_id}-" in upper_file or
                    f"-{raw_id}-" in upper_file
                )

                if is_id_match:
                    if target_kw:
                        if target_kw in upper_file:
                            matched_files.append(os.path.join(root, file))
                    else:
                        matched_files.append(os.path.join(root, file))

    # If no kw specific match found, fallback to any file matching ID
    if not matched_files and target_kw:
        for sdir in search_dirs:
            for root, _, files in os.walk(sdir):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        upper_file = file.upper()
                        if upper_file.startswith(f"{item_id}-") or upper_file.startswith(f"{raw_id}-"):
                            matched_files.append(os.path.join(root, file))

    return sorted(list(set(matched_files)))

def process_sku_list_copy(skus, anhlocal_dir, job_dest_folder):
    """
    Parses list of SKUs, finds corresponding SANG/TOI images from ANHLOCAL,
    and copies them to the isolated job_dest_folder.
    Returns dict with summary log and list of copied files.
    """
    os.makedirs(job_dest_folder, exist_ok=True)
    copied_files = []
    logs = []
    sku_results = []

    logs.append(f"📁 Thư mục nguồn ANHLOCAL: {anhlocal_dir}")
    logs.append(f"📂 Thư mục đích Print Job riêng biệt: {job_dest_folder}")

    for idx, sku_str in enumerate(skus, start=1):
        sku_info = parse_sku(sku_str)
        is_valid_sku = bool(sku_info)
        if not sku_info:
            logs.append(f"❌ LỖI SKU SAI ĐỊNH DẠNG [{idx}/{len(skus)}]: SKU '{sku_str}' không khớp định dạng [ID]-[ÁO]-[SIZE] (Ví dụ đúng: 03-D-XL)!")
            sku_info = {"id": sku_str, "raw_id": sku_str, "color": "UNKNOWN"}

        found_images = find_matching_images(sku_info, anhlocal_dir)
        if found_images:
            logs.append(f"✅ SKU [{sku_str}] (Áo {sku_info['color']}) -> Tìm thấy {len(found_images)} file ảnh:")
            for img_path in found_images:
                fname = os.path.basename(img_path)
                base_name, ext = os.path.splitext(fname)
                
                # Ensure unique destination filename if SKU quantity > 1 (e.g. 03-TOI-TRUOC_copy2.png)
                unique_dest_path = os.path.join(job_dest_folder, fname)
                copy_idx = 1
                while os.path.exists(unique_dest_path):
                    copy_idx += 1
                    unique_dest_path = os.path.join(job_dest_folder, f"{base_name}_qty{copy_idx}{ext}")

                shutil.copy2(img_path, unique_dest_path)
                copied_files.append(unique_dest_path)
                dest_fname = os.path.basename(unique_dest_path)
                logs.append(f"   + Copy ({dest_fname}) -> {job_dest_folder}")
        else:
            logs.append(f"❌ LỖI KHÔNG TÌM THẤY ẢNH [{idx}/{len(skus)}]: SKU [{sku_str}] (Áo {sku_info.get('color', 'N/A')}) -> Không tìm thấy file ảnh SANG/TOI phù hợp trong thư mục ANHLOCAL ({anhlocal_dir})!")

        if not is_valid_sku:
            error_message = f"SKU '{sku_str}' không khớp định dạng [ID]-[ÁO]-[SIZE]"
        elif not found_images:
            error_message = f"Không tìm thấy ảnh SANG/TOI cho SKU '{sku_str}' trong ANHLOCAL"
        else:
            error_message = ""
        sku_results.append({
            "sku": sku_str or "NOSKU",
            "success": is_valid_sku and bool(found_images),
            "matched_count": len(found_images),
            "error_message": error_message,
        })

    return {
        "success": len(copied_files) > 0,
        "copied_count": len(copied_files),
        "copied_files": copied_files,
        "sku_results": sku_results,
        "logs": logs
    }
