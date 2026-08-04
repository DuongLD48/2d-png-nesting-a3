import os
import json
import http.server
import socketserver
import urllib.parse
from src.config_loader import ConfigLoader
from main import run_nesting_pipeline

PORT = 8000

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2D PNG Nesting Engine A3 - Web Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --panel-bg: #1e293b;
            --accent-color: #38bdf8;
            --accent-hover: #0284c7;
            --text-color: #f8fafc;
            --muted-text: #94a3b8;
            --border-color: #334155;
            --success-color: #4ade80;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-color); padding: 24px; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid var(--border-color); padding-bottom: 16px; }
        h1 { font-size: 24px; font-weight: 700; color: var(--accent-color); }
        .subtitle { color: var(--muted-text); font-size: 14px; margin-top: 4px; }
        .grid { display: grid; grid-template-columns: 360px 1fr; gap: 24px; }
        .card { background-color: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }
        .card-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; color: var(--accent-color); }
        .form-group { margin-bottom: 14px; }
        label { display: block; font-size: 13px; font-weight: 600; color: var(--muted-text); margin-bottom: 6px; }
        input, select, textarea { width: 100%; background: #0f172a; border: 1px solid var(--border-color); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 14px; }
        textarea { font-family: monospace; font-size: 12px; height: 320px; }
        button { width: 100%; background: var(--accent-color); color: #0f172a; border: none; font-weight: 700; padding: 12px; border-radius: 8px; cursor: pointer; font-size: 15px; transition: all 0.2s; }
        button:hover { background: var(--accent-hover); color: #fff; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-top: 16px; }
        .gallery-item { background: #0f172a; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
        .gallery-item img { width: 100%; display: block; border-bottom: 1px solid var(--border-color); background: #fff; }
        .gallery-caption { padding: 12px; font-size: 14px; font-weight: 600; text-align: center; }
        .badge { background: rgba(74, 222, 128, 0.2); color: var(--success-color); padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        pre { background: #0f172a; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; border: 1px solid var(--border-color); }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>🎨 2D PNG Nesting Engine A3 - Web Dashboard</h1>
            <div class="subtitle">Quản lý tham số qua config.json & Xem trước kết quả xếp trang A3</div>
        </div>
        <div class="badge">Zero Hardcoding Enabled</div>
    </header>

    <div class="grid">
        <div class="card">
            <div class="card-title">⚙ Cấu Hình Config.json</div>
            <form action="/save_config" method="POST">
                <div class="form-group">
                    <label>JSON Config (Sửa trực tiếp):</label>
                    <textarea name="config_content">{CONFIG_JSON}</textarea>
                </div>
                <button type="submit">💾 Lưu Config & Run Nesting</button>
            </form>
        </div>

        <div class="card">
            <div class="card-title">🖼 Kết Quả Render Trang A3 ({TOTAL_SHEETS} trang)</div>
            <div class="gallery">
                {IMAGE_GALLERY}
            </div>
            
            <div class="card-title" style="margin-top: 24px;">📊 Layout JSON & Report Data</div>
            <p style="margin-bottom: 8px; color: var(--muted-text); font-size: 13px;">File xuất tại <code>{OUTPUT_DIR}</code></p>
            <pre>{REPORT_PREVIEW}</pre>
        </div>
    </div>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            config_path = "config.json"
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config_json_str = f.read()
            else:
                config_json_str = "{}"

            output_dir = "output"
            gallery_html = ""
            total_sheets = 0
            if os.path.exists(output_dir):
                pngs = sorted([f for f in os.listdir(output_dir) if f.startswith("A3_") and f.endswith(".png")])
                total_sheets = len(pngs)
                for png in pngs:
                    img_url = f"/output/{png}"
                    gallery_html += f"""
                    <div class="gallery-item">
                        <a href="{img_url}" target="_blank">
                            <img src="{img_url}" alt="{png}">
                        </a>
                        <div class="gallery-caption">{png}</div>
                    </div>
                    """
            if not gallery_html:
                gallery_html = "<p style='color: #94a3b8;'>Chưa có kết quả. Nhấn 'Lưu Config & Run Nesting' để chạy thử!</p>"

            report_csv_path = os.path.join(output_dir, "report.csv")
            report_preview = ""
            if os.path.exists(report_csv_path):
                with open(report_csv_path, "r", encoding="utf-8") as f:
                    report_preview = f.read()
            else:
                report_preview = "Chưa tìm thấy file report.csv"

            html = HTML_TEMPLATE.replace("{CONFIG_JSON}", config_json_str)
            html = html.replace("{IMAGE_GALLERY}", gallery_html)
            html = html.replace("{TOTAL_SHEETS}", str(total_sheets))
            html = html.replace("{OUTPUT_DIR}", output_dir)
            html = html.replace("{REPORT_PREVIEW}", report_preview)

            self.wfile.write(html.encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/save_config":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed = urllib.parse.parse_qs(post_data)
            
            if 'config_content' in parsed:
                new_config_str = parsed['config_content'][0]
                try:
                    # Validate JSON
                    json_obj = json.loads(new_config_str)
                    with open("config.json", "w", encoding="utf-8") as f:
                        json.dump(json_obj, f, indent=2, ensure_ascii=False)
                    
                    # Run nesting pipeline
                    run_nesting_pipeline("config.json")
                except Exception as e:
                    print(f"Lỗi khi chạy Nesting: {e}")

            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

def start_server():
    os.makedirs("output", exist_ok=True)
    os.makedirs("pngfile", exist_ok=True)
    
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🌐 Dashboard đang chạy tại: http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐang dừng Web Dashboard...")

if __name__ == "__main__":
    start_server()
