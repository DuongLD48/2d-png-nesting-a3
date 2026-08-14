import os
import json
import time
import shutil
import datetime
import traceback
import urllib.parse
import urllib.request
from typing import Dict, Any, List

from src.sku_processor import process_sku_list_copy
from src.config_loader import ConfigLoader
from src.preprocessor import Preprocessor
from src.geometry import NormalizedGeometry
from src.sorter import PrioritySorter
from src.nesting_engine import NestingEngine
from src.renderer import RenderEngine
from src.validator import QualityChecker
from src.exporter import Exporter

LOCAL_CONFIG_PATH = "local_config.json"

def write_sku_history_entries(job_data: Dict[str, Any], sku_results: List[Dict[str, Any]], pipeline_error: str = "") -> None:
    """Persist the actual processing outcome of each SKU to Firestore."""
    firebase = load_local_config().get("firebase", {})
    project_id = firebase.get("projectId", "order-web-hoang")
    api_key = firebase.get("apiKey", "")
    if not project_id or not api_key:
        print("[SKU History] Firebase configuration is missing.", flush=True)
        return

    job_id = str(job_data.get("id", "JOB-UNKNOWN"))
    order_id = str(job_data.get("order_id", ""))
    job_type = str(job_data.get("job_type", "custom_nesting"))
    job_label = str(job_data.get("job_type_label") or job_type)
    for index, result in enumerate(sku_results):
        success = bool(result.get("success")) and not pipeline_error
        entry_id = f"{job_id}-SKU-{index}"
        entry = {
            "id": entry_id, "job_id": job_id,
            "sku": str(result.get("sku") or "NOSKU"),
            "name": f"SKU: {result.get('sku') or 'NOSKU'}",
            "order_id": order_id, "sapo_order_code": order_id,
            "job_type": job_type, "job_type_label": job_label,
            "status": "success" if success else "failed",
            "timestamp": datetime.datetime.now().isoformat(),
            "error_message": str(pipeline_error or result.get("error_message", "")),
            "note": (f"Processed {result.get('matched_count', 0)} image file(s) from ANHLOCAL"
                     if success else "SKU could not be processed; see error detail"),
        }
        fields = {key: {"stringValue": value} for key, value in entry.items()}
        url = (
            f"https://firestore.googleapis.com/v1/projects/{urllib.parse.quote(project_id, safe='')}"
            f"/databases/(default)/documents/sku_history/{urllib.parse.quote(entry_id, safe='')}"
            f"?key={urllib.parse.quote(api_key, safe='')}"
        )
        try:
            request = urllib.request.Request(
                url, data=json.dumps({"fields": fields}).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="PATCH"
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status not in (200, 201):
                    raise RuntimeError(f"HTTP {response.status}")
            print(f"[SKU History] Recorded {entry['sku']} -> {entry['status']}", flush=True)
        except Exception as error:
            print(f"[SKU History] Could not record {entry['sku']}: {error}", flush=True)

def get_config_file_path() -> str:
    candidates = [
        "local_config.json",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_config.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "local_config.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "NESTING", "local_config.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_config.json")

def get_valid_path(path_str: str, default_relative: str) -> str:
    if not path_str:
        path_str = default_relative
    try:
        if os.path.isabs(path_str) and os.path.exists(path_str):
            return os.path.abspath(path_str)
        
        # Check relative candidates
        cur_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        nesting_root_dir = os.path.dirname(cur_backend_dir)
        workspace_root = os.path.dirname(nesting_root_dir)

        candidates = [
            os.path.abspath(path_str),
            os.path.join(cur_backend_dir, path_str),
            os.path.join(nesting_root_dir, path_str),
            os.path.join(workspace_root, path_str),
            os.path.join(cur_backend_dir, default_relative),
            os.path.join(nesting_root_dir, default_relative),
            os.path.join(workspace_root, default_relative)
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return os.path.join(nesting_root_dir, default_relative)
    except Exception:
        return os.path.abspath(default_relative)

def load_local_config() -> Dict[str, Any]:
    cfg_path = get_config_file_path()
    if not os.path.exists(cfg_path):
        default_config = {
            "anhlocal_dir": "ANHLOCAL",
            "output_dir": "output",
            "custom_nesting": {
                "paper_size": "Custom (390x290mm)",
                "width_mm": 390.0,
                "height_mm": 290.0,
                "dpi": 300,
                "padding_mm": 3.0,
                "margin_top_mm": 0.0,
                "margin_bottom_mm": 0.0,
                "margin_left_mm": 0.0,
                "margin_right_mm": 0.0,
                "rotation_angles_deg": [0, 90, 180, 270],
                "auto_scale_oversized": False
            },
            "pet_nesting": {
                "paper_size": "PET Roll (580x1000mm)",
                "width_mm": 580.0,
                "height_mm": 1000.0,
                "dpi": 300,
                "padding_mm": 5.0,
                "margin_top_mm": 0.0,
                "margin_bottom_mm": 0.0,
                "margin_left_mm": 0.0,
                "margin_right_mm": 0.0,
                "rotation_angles_deg": [0, 90, 180, 270],
                "auto_scale_oversized": False
            },
            "firebase": {
                "projectId": "order-web-hoang",
                "apiKey": "AIzaSyC1SK8dB0FSz00EkeXErBdgp-SOeUj-HCU",
                "auto_listen": True
            }
        }
        save_local_config(default_config)
        return default_config
    
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            cfg["anhlocal_dir"] = get_valid_path(cfg.get("anhlocal_dir"), "ANHLOCAL")
            cfg["output_dir"] = get_valid_path(cfg.get("output_dir"), "output")
            return cfg
    except Exception:
        return {
            "anhlocal_dir": get_valid_path("", "ANHLOCAL"),
            "output_dir": get_valid_path("", "output")
        }

def save_local_config(config_data: Dict[str, Any]) -> bool:
    try:
        cfg_path = get_config_file_path()
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving local config: {e}")
        return False

def run_job_execution(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a print job locally:
    1. Reads configuration from local_config.json
    2. Creates a unique destination folder: output/JOB_[TIMESTAMP]_[JOB_ID]/
    3. Copies matching SANG/TOI images for the SKUs
    4. Performs DTG, Custom Nesting, or PET Nesting
    5. Returns execution log and status result
    """
    job_id = job_data.get("id", f"JOB-{int(time.time())}")
    order_id = job_data.get("order_id", "UNKNOWN")
    skus = job_data.get("skus", [])
    job_type = job_data.get("job_type", "custom_nesting")
    
    local_cfg = load_local_config()
    anhlocal_dir = get_valid_path(local_cfg.get("anhlocal_dir"), "ANHLOCAL")
    base_output_dir = get_valid_path(local_cfg.get("output_dir"), "output")

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Simple clean folder name: JOB_YYYYMMDD_HHMMSS (no long order names)
    job_folder_name = f"JOB_{timestamp_str}"
    job_output_folder = os.path.join(base_output_dir, job_folder_name)
    
    # Handle duplicate timestamp edge case
    counter = 1
    while os.path.exists(job_output_folder):
        job_folder_name = f"JOB_{timestamp_str}_{counter}"
        job_output_folder = os.path.join(base_output_dir, job_folder_name)
        counter += 1

    job_input_folder = os.path.join(job_output_folder, "inputs")
    os.makedirs(job_input_folder, exist_ok=True)
    os.makedirs(job_output_folder, exist_ok=True)

    logs = []
    def log_msg(msg):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
        logs.append(msg)

    log_msg(f"🚀 [PRINT JOB] Bắt đầu thực thi Job ID: {job_id} | Đơn hàng: {order_id}")
    log_msg(f"🏷️ Loại tác vụ: {job_type.upper()}")
    log_msg(f"📦 Danh sách SKU: {', '.join(skus) if skus else 'Rỗng'}")
    log_msg(f"📁 Thư mục đầu ra cách ly: {job_output_folder}")

    # Step 1: Copy SANG/TOI images from ANHLOCAL
    log_msg(" -> [BƯỚC 1/6] Đang tìm kiếm & copy file ảnh SANG/TOI từ ANHLOCAL...")
    copy_res = process_sku_list_copy(skus, anhlocal_dir, job_input_folder)
    for l in copy_res["logs"]:
        log_msg(l)

    # Write full job metadata & order list into job_summary.json inside the job output folder
    job_summary_data = {
        "job_id": job_id,
        "order_ids": order_id,
        "job_type": job_type,
        "skus": skus,
        "created_at": datetime.datetime.now().isoformat(),
        "copied_count": copy_res.get("copied_count", 0),
        "copied_files": [os.path.basename(f) for f in copy_res.get("copied_files", [])]
    }
    with open(os.path.join(job_output_folder, "job_summary.json"), "w", encoding="utf-8") as f:
        json.dump(job_summary_data, f, indent=2, ensure_ascii=False)

    if not copy_res["copied_files"]:
        log_msg("⚠️ Cảnh báo: Không có file ảnh nào được copy! Vui lòng kiểm tra SKU hoặc file ảnh trong ANHLOCAL.")

    rendered_files = []
    total_sheets = 0
    pipeline_error = ""

    # Step 2: Handle Job Type
    if job_type == "dtg":
        log_msg("🖨️ [IN DTG] Chỉ copy file ảnh thành công vào folder riêng. Hoàn tất tác vụ DTG!")
        # Copy image files to root of job_output_folder for easy access
        for img in copy_res["copied_files"]:
            shutil.copy2(img, os.path.join(job_output_folder, os.path.basename(img)))
            rendered_files.append(os.path.basename(img))
    
    elif job_type in ["custom_nesting", "pet_nesting"]:
        nest_key = "custom_nesting" if job_type == "custom_nesting" else "pet_nesting"
        nest_settings = local_cfg.get(nest_key, {})
        log_msg(f"📐 [{nest_key.upper()}] Áp dụng cấu hình: Khổ {nest_settings.get('width_mm')}x{nest_settings.get('height_mm')}mm, DPI: {nest_settings.get('dpi')}, Padding: {nest_settings.get('padding_mm')}mm")

        # Build runtime config object matching Nesting Engine standard
        runtime_config_dict = {
            "canvas": {
                "paper_size": nest_settings.get("paper_size", "Custom"),
                "width_mm": float(nest_settings.get("width_mm", 390.0)),
                "height_mm": float(nest_settings.get("height_mm", 290.0)),
                "dpi": int(nest_settings.get("dpi", 300)),
                "margin_top_mm": float(nest_settings.get("margin_top_mm", 0.0)),
                "margin_bottom_mm": float(nest_settings.get("margin_bottom_mm", 0.0)),
                "margin_left_mm": float(nest_settings.get("margin_left_mm", 0.0)),
                "margin_right_mm": float(nest_settings.get("margin_right_mm", 0.0)),
                "background_color_rgba": [255, 255, 255, 0]
            },
            "preprocessing": {
                "alpha_threshold": 10,
                "contour_approx_epsilon": 0.003,
                "min_contour_area_px": 20.0,
                "auto_scale_oversized": nest_settings.get("auto_scale_oversized", False),
                "use_embedded_dpi": True,
                "default_input_dpi": "match_canvas",
                "max_item_dimension_mm": 280.0
            },
            "nesting": {
                "padding_mm": float(nest_settings.get("padding_mm", 3.0)),
                "enable_360_rotation": True,
                "rotation_step_deg": 15,
                "center_layout": True,
                "center_in_printable_area": True,
                "rotation_angles_deg": nest_settings.get("rotation_angles_deg", [0, 90, 180, 270]),
                "strategy": "bottom_left_fill",
                "search_step_px": 10,
                "use_spatial_index": True,
                "max_sheets_limit": 50
            },
            "sorting": {
                "primary_key": "area",
                "secondary_key": "complexity",
                "tertiary_key": "aspect_ratio",
                "reverse": True
            },
            "rendering": {
                "resampling_filter": "bicubic",
                "anti_aliasing": True
            },
            "quality_check": {
                "allow_overlap": False,
                "enforce_margins": True,
                "enforce_padding": True,
                "tolerance_px": 2.0
            },
            "paths": {
                "input_folder": job_input_folder,
                "output_folder": job_output_folder,
                "layout_filename": "layout.json",
                "report_filename": "report.csv"
            }
        }

        # Save temporary runtime config file in job folder
        runtime_config_path = os.path.join(job_output_folder, "job_config.json")
        with open(runtime_config_path, "w", encoding="utf-8") as f:
            json.dump(runtime_config_dict, f, indent=2, ensure_ascii=False)

        # Run Nesting Pipeline
        try:
            config = ConfigLoader(runtime_config_path)
            preprocessor = Preprocessor(config)
            raw_items = preprocessor.load_all_from_folder(job_input_folder)

            if raw_items:
                log_msg(f" -> Đã đọc & tiền xử lý thành công {len(raw_items)} hình vẽ.")
                log_msg(" -> [BƯỚC 4/6] Đang chuẩn hóa hình học & sắp xếp hình ưu tiên...")
                normalized_items = [NormalizedGeometry(item) for item in raw_items]
                sorter = PrioritySorter(config)
                sorted_items = sorter.sort(normalized_items)

                log_msg(" -> [BƯỚC 5/6] Đang chạy thuật toán Nesting Engine 2D...")
                nesting_engine = NestingEngine(config)
                sheets = nesting_engine.nest_all(sorted_items)
                total_sheets = len(sheets)
                log_msg(f" -> [BƯỚC 5/6] Xếp xong toàn bộ hình lên {total_sheets} trang in.")

                log_msg(" -> [BƯỚC 6/6] Đang render ảnh PNG chất lượng cao & xuất file layout.json, report.csv...")
                renderer = RenderEngine(config)
                rendered_paths = renderer.render_and_save_all(sheets, job_output_folder)
                rendered_files = [os.path.basename(p) for p in rendered_paths]

                validator = QualityChecker(config)
                is_valid, issues, stats = validator.validate_all(sheets)

                exporter = Exporter(config)
                exporter.export_layout_json(sheets, job_output_folder)
                exporter.export_report_csv(stats, job_output_folder)
                log_msg("✅ Hoàn tất render ảnh PNG, file layout.json & báo cáo report.csv!")
            else:
                log_msg("⚠️ Cảnh báo: Thư mục input không chứa file PNG hợp lệ nào để xếp khổ.")
        except Exception as e:
            pipeline_error = f"Nesting pipeline error: {e}"
            log_msg(f"❌ Lỗi khi chạy Nesting Pipeline: {e}")
            log_msg(traceback.format_exc())

    write_sku_history_entries(job_data, copy_res.get("sku_results", []), pipeline_error)
    log_msg(f"🎉 [PRINT JOB COMPLETED] Hoàn thành xử lý Job {job_id}!")
    
    return {
        "job_id": job_id,
        "order_id": order_id,
        "job_type": job_type,
        "status": "completed",
        "job_output_folder": job_output_folder,
        "relative_folder": os.path.basename(job_output_folder),
        "total_sheets": total_sheets,
        "rendered_files": rendered_files,
        "sku_results": copy_res.get("sku_results", []),
        "logs": logs
    }
