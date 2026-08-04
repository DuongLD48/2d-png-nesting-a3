# 🎨 2D PNG Nesting Engine Khổ A3 (Python)

Ứng dụng Python tự động sắp xếp (**2D Nesting**) hàng loạt các file ảnh PNG (có kênh Alpha trong suốt) lên các trang A3 tối ưu diện tích, chống chồng đè (Collision-free) và tự động xuất ra ảnh render chất lượng cao, file tọa độ `layout.json` và báo cáo `report.csv`.

> 🛡 **ZERO HARDCODING RULE**: 100% tham số hệ thống (Kích thước A3, DPI, Margins, Padding, Góc xoay, Tiêu chí sắp xếp, Màu nền canvas, Ngưỡng Alpha, Đường dẫn file/folder) đều được nạp động từ file [`config.json`](config.json).

---

## 🚀 Tính Năng Nổi Bật

- 📐 **Trích xuất viền thực tế (Contour Parsing)**: Tách kênh Alpha để lấy đường viền Polygon thực tế của hình vẽ thay vì chỉ lấy Bounding Box thô.
- 🔄 **Xoay hình linh hoạt**: Hỗ trợ xoay hình theo danh sách góc cấu hình (ví dụ: `0°`, `90°`, `180°`, `270°` hoặc fine-grained step).
- ⚡ **Spatial R-Tree Indexing**: Sử dụng `Shapely STRtree` giúp thuật toán phát hiện va chạm (Collision Detection) siêu nhanh.
- 🎯 **Sắp xếp ưu tiên đa tầng (Priority Sorting)**:
  1. Hình diện tích lớn trước (`area`)
  2. Hình phức tạp/lõm trước (`complexity`)
  3. Hình dài trước (`aspect_ratio`)
- 📄 **Tự động mở nhiều trang A3**: Khi trang A3 hiện tại hết chỗ, tự động sinh trang mới (`A3_001.png`, `A3_002.png`, `A3_003.png`,...).
- 🎨 **Alpha Blending & Resampling BICUBIC**: Render ảnh PNG đầu ra sắc nét, giữ nguyên độ trong suốt và màu sắc.
- 🔍 **Quality Checker tự động**: Đảm bảo 100% không đè hình (Overlap), không tràn viền A3, đủ khoảng cách Padding.
- 🌐 **Web Dashboard Interactive**: Giao diện Web trực quan hỗ trợ sửa `config.json` và xem trước các trang A3 ngay trên trình duyệt.

---

## 🛠 Cấu Trúc Dự Án

```text
NESTING/
├── config.json                # File cấu hình duy nhất quản lý 100% tham số dự án
├── pngfile/                   # Thư mục chứa các file PNG đầu vào
├── output/                    # Thư mục chứa kết quả xuất (A3_xxx.png, layout.json, report.csv)
├── src/
│   ├── config_loader.py       # Nạp và tính toán tham số mm -> px theo DPI
│   ├── preprocessor.py        # Tiền xử lý PNG, Alpha Channel, Contour Extraction
│   ├── geometry.py            # Polygon Normalization, Convex Hull, Coordinate Transformation
│   ├── sorter.py              # Priority Sorting Engine
│   ├── nesting_engine.py      # Core 2D Nesting Algorithm & Collision Detection
│   ├── renderer.py            # PIL A3 Canvas Render & Alpha Blending
│   ├── validator.py           # Quality Checker (Overlap, Boundaries, Padding)
│   └── exporter.py            # Ghi layout.json và report.csv
├── tests/
│   └── generate_test_pngs.py  # Script sinh dữ liệu PNG kiểm thử
├── main.py                    # Pipeline Runner chính (CLI)
├── app.py                     # Web GUI Dashboard (http://localhost:8000)
├── requirements.txt           # Danh sách thư viện Python
└── README.md                  # Tài liệu hướng dẫn dự án
```

---

## 💻 Cài Đặt & Sử Dụng

### 1. Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### 2. Chạy Pipeline bằng dòng lệnh (CLI)
```bash
python main.py --config config.json
```

### 3. Mở Giao diện Web Interactive Dashboard
```bash
python app.py
```
Mở trình duyệt và truy cập: **`http://localhost:8000`**

---

## ⚙ Quản Lý Cấu Hình (`config.json`)

```json
{
  "canvas": {
    "paper_size": "A3",
    "width_mm": 297.0,
    "height_mm": 420.0,
    "dpi": 150,
    "margin_top_mm": 5.0,
    "margin_bottom_mm": 5.0,
    "margin_left_mm": 5.0,
    "margin_right_mm": 5.0,
    "background_color_rgba": [255, 255, 255, 0]
  },
  "preprocessing": {
    "alpha_threshold": 10,
    "contour_approx_epsilon": 0.003,
    "min_contour_area_px": 20.0,
    "auto_scale_oversized": true,
    "max_item_dimension_mm": 280.0
  },
  "nesting": {
    "padding_mm": 3.0,
    "rotation_angles_deg": [0, 90, 180, 270],
    "strategy": "bottom_left_fill",
    "search_step_px": 10,
    "use_spatial_index": true,
    "max_sheets_limit": 50
  },
  "sorting": {
    "primary_key": "area",
    "secondary_key": "complexity",
    "tertiary_key": "aspect_ratio",
    "reverse": true
  },
  "quality_check": {
    "allow_overlap": false,
    "enforce_margins": true,
    "enforce_padding": true,
    "tolerance_px": 0.5
  },
  "paths": {
    "input_folder": "pngfile",
    "output_folder": "output",
    "layout_filename": "layout.json",
    "report_filename": "report.csv"
  }
}
```

---

## 📊 Mẫu Kết Quả Báo Cáo CSV (`report.csv`)

| sheet_index | total_items | used_area_px | printable_area_px | waste_area_px | efficiency_percent |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 6 | 3,087,759 | 4,103,368 | 988,046 | 75.25% |
| 2 | 9 | 2,915,760 | 4,103,368 | 1,174,325 | 71.06% |
| **TOTAL / AVG** | **56** | **23,694,267** | **65,653,890** | **41,959,622** | **36.09%** |
