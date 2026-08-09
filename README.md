# 🎨 2D PNG Nesting Engine (Python)

Ứng dụng Python tự động sắp xếp (**2D Nesting**) hàng loạt các file ảnh PNG (có kênh Alpha trong suốt) lên các trang giấy tối ưu diện tích, chống chồng đè (Collision-free) và tự động xuất ra ảnh render chất lượng cao, file tọa độ `layout.json` và báo cáo `report.csv`.

> 🛡 **ZERO HARDCODING RULE**: 100% tham số hệ thống (Kích thước khổ giấy, DPI, Margins, Padding, Góc xoay 360°, Tiêu chí sắp xếp, Màu nền canvas, Ngưỡng Alpha, Đường dẫn file/folder) đều được nạp động từ file [`config.json`](config.json).

---

## ⚡ Cách Nhanh Nhất (Dành Cho Windows)

1. Tải file [`CLONE.bat`](CLONE.bat) về máy và nhấp đúp chuột để chạy.
2. Script sẽ tự động:
   - `git clone` repository về máy.
   - Cài đặt toàn bộ thư viện Python (`requirements.txt`).
   - Chạy trực tiếp ứng dụng Nesting!

---

## 🚀 Tính Năng Nổi Bật

- 📏 **Giữ nguyên 100% kích thước ảnh gốc**: Không tự động scale hay làm bóp méo sai lệch kích thước in thực tế (`"auto_scale_oversized": false`).
- 🚫 **Tự động bỏ qua file quá khổ**: Tự động nhận biết file có kích thước lớn hơn khổ giấy ở mọi góc xoay, in cảnh báo ra Console Log và bỏ qua file đó để tránh tốn giấy.
- 📐 **Trích xuất viền thực tế (Contour Parsing)**: Tách kênh Alpha để lấy đường viền Polygon/MultiPolygon thực tế của hình vẽ (hỗ trợ cả đoạn văn bản nhiều chữ cái rời rạc).
- 🔄 **Xoay tự do 360° & DFS Re-Packing**: Hỗ trợ xoay góc bất kỳ và thuật toán Re-Packing tự chọn hướng xoay dọc/ngang tối ưu xếp nhiều hình nhất trên 1 trang (Ví dụ: 2 hình 19x29 cm xếp vừa khít trên 1 trang 40x30 cm).
- ⚡ **Spatial R-Tree Indexing**: Sử dụng `Shapely STRtree` giúp thuật toán phát hiện va chạm (Collision Detection) siêu nhanh.
- 📄 **Tự động mở nhiều trang**: Khi trang hiện tại hết chỗ, tự động sinh trang mới (`A3_001.png`, `A3_002.png`, `A3_003.png`,...).
- 🎨 **Alpha Blending & Resampling BICUBIC**: Render ảnh PNG đầu ra sắc nét, giữ nguyên độ trong suốt và màu sắc.
- 🔍 **Quality Checker tự động**: Đảm bảo 100% không đè hình (Overlap), không tràn viền, đủ khoảng cách Padding.
- 🌐 **Web Dashboard Interactive**: Giao diện Web trực quan hỗ trợ sửa `config.json` và xem trước các trang ngay trên trình duyệt (`python app.py`).

---

## 🛠 Cấu Trúc Dự Án

```text
NESTING/
├── CLONE.bat                  # Script 1-click tự động clone & setup dự án trên Windows
├── RUN.bat                    # Script menu chạy ứng dụng CLI / Web GUI
├── config.json                # File cấu hình duy nhất quản lý 100% tham số dự án
├── pngfile/                   # Thư mục chứa các file PNG đầu vào
├── output/                    # Thư mục chứa kết quả xuất (A3_xxx.png, layout.json, report.csv)
├── src/
│   ├── config_loader.py       # Nạp và tính toán tham số mm -> px theo DPI
│   ├── preprocessor.py        # Tiền xử lý PNG, Alpha Channel, Contour Extraction
│   ├── geometry.py            # Polygon/MultiPolygon Normalization & Transformation
│   ├── sorter.py              # Priority Sorting Engine
│   ├── nesting_engine.py      # Core 2D Nesting Algorithm, 360° Rotation & DFS Re-Packing
│   ├── renderer.py            # PIL Canvas Render & Alpha Blending
│   ├── validator.py           # Quality Checker (Overlap, Boundaries, Padding)
│   └── exporter.py            # Ghi layout.json và report.csv
├── tests/
│   ├── generate_test_pngs.py  # Script sinh dữ liệu PNG kiểm thử
│   └── test_user_scenario.py  # Unit test kiểm thử kịch bản khổ 40x30 cm với 2 hình 19x29 cm
├── main.py                    # Pipeline Runner chính (CLI)
├── app.py                     # Web GUI Dashboard (http://localhost:8000)
├── requirements.txt           # Danh sách thư viện Python
└── README.md                  # Tài liệu hướng dẫn dự án
```

---

## 💻 Cài Đặt & Sử Dụng Thủ Công

### 1. Clone & Cài đặt thư viện
```bash
git clone https://github.com/DuongLD48/2d-png-nesting-a3.git
cd 2d-png-nesting-a3
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
