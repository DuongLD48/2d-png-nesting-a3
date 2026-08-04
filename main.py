import os
import sys
import argparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config_loader import ConfigLoader
from src.preprocessor import Preprocessor
from src.geometry import NormalizedGeometry
from src.sorter import PrioritySorter
from src.nesting_engine import NestingEngine
from src.renderer import RenderEngine
from src.validator import QualityChecker
from src.exporter import Exporter

console = Console()

def run_nesting_pipeline(config_path: str = "config.json"):
    console.print(Panel("[bold green]Ứng Dụng Python 2D PNG Nesting Khổ A3[/bold green]\n[cyan]Tự động sắp xếp tối ưu diện tích & xuất kết quả[/cyan]"))

    # Step 0: Load Config (Zero Hardcoding Rule)
    console.print(f"[yellow][Step 0][/yellow] Đọc file cấu hình: [bold]{config_path}[/bold]")
    config = ConfigLoader(config_path)
    
    input_folder = config.paths.get("input_folder", "pngfile")
    output_folder = config.paths.get("output_folder", "output")

    # Step 1 & 2: Read PNGs & Pre-processing
    console.print(f"[yellow][Step 1 & 2][/yellow] Đọc PNG & Tiền xử lý từ thư mục '[bold]{input_folder}[/bold]'...")
    preprocessor = Preprocessor(config)
    raw_items = preprocessor.load_all_from_folder(input_folder)

    if not raw_items:
        console.print(f"[bold red]Cảnh báo:[/bold red] Không tìm thấy file PNG nào trong thư mục '{input_folder}'!")
        console.print(f"[dim]Vui lòng copy các file PNG vào thư mục '{input_folder}' rồi chạy lại.[/dim]")
        return

    console.print(f" -> Đã đọc thành công [bold green]{len(raw_items)}[/bold green] file PNG.")

    # Step 3: Normalize Geometry
    console.print("[yellow][Step 3][/yellow] Chuẩn hóa dữ liệu hình học (Polygon, Convex Hull, Centroid)...")
    normalized_items = [NormalizedGeometry(item) for item in raw_items]

    # Step 4: Priority Sorting
    console.print("[yellow][Step 4][/yellow] Sắp xếp ưu tiên (Hình lớn trước, Phức tạp trước, Hình dài trước)...")
    sorter = PrioritySorter(config)
    sorted_items = sorter.sort(normalized_items)

    # Step 5: Nesting Engine
    console.print("[yellow][Step 5][/yellow] Đang thực hiện Nesting Engine (Collision Detection & Xoay hình)...")
    nesting_engine = NestingEngine(config)
    sheets = nesting_engine.nest_all(sorted_items)
    console.print(f" -> Kết quả: Đã xếp toàn bộ vật thể lên [bold cyan]{len(sheets)}[/bold cyan] trang A3.")

    # Step 6: Render Engine
    console.print("[yellow][Step 6][/yellow] Render hình ảnh PNG khổ A3 chất lượng cao...")
    renderer = RenderEngine(config)
    rendered_image_paths = renderer.render_and_save_all(sheets, output_folder)

    # Step 7: Quality Check
    console.print("[yellow][Step 7][/yellow] Thực hiện Quality Check (Overlap, Boundaries, Padding)...")
    validator = QualityChecker(config)
    is_valid, issues, stats = validator.validate_all(sheets)

    if is_valid:
        console.print("[bold green]✔ Quality Check PASSED:[/bold green] Layout hoàn toàn hợp lệ, không đè hình, không tràn viền!")
    else:
        console.print(f"[bold red]✘ Quality Check FAILED:[/bold red] Phát hiện {len(issues)} vấn đề:")
        for issue in issues[:5]: # print first 5 issues
            console.print(f"  - [red]{issue}[/red]")

    # Step 8: Export Results
    console.print("[yellow][Step 8][/yellow] Xuất kết quả layout.json và report.csv...")
    exporter = Exporter(config)
    json_path = exporter.export_layout_json(sheets, output_folder)
    csv_path = exporter.export_report_csv(stats, output_folder)

    # Summary Table
    table = Table(title="[bold yellow]Báo Cáo Tổng Quan Nesting[/bold yellow]")
    table.add_column("Trang A3", style="cyan")
    table.add_column("Số Hình", style="magenta")
    table.add_column("Diện Tích Sử Dụng (px²)", style="green")
    table.add_column("Hiệu Suất (%)", style="yellow")

    for stat in stats:
        table.add_row(
            f"A3_{stat['sheet_index']:03d}",
            str(stat['total_items']),
            f"{stat['used_area_px']:,.0f}",
            f"{stat['efficiency_percent']:.2f}%"
        )

    console.print(table)
    console.print(f"[bold green]🎉 Hoàn tất toàn bộ quy trình![/bold green] Kết quả đã lưu tại thư mục '[bold]{output_folder}[/bold]'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python 2D PNG Nesting Engine A3")
    parser.add_argument("--config", type=str, default="config.json", help="Đường dẫn file JSON cấu hình")
    args = parser.parse_args()

    run_nesting_pipeline(args.config)
