import sys
import os
import json
import traceback

# Ensure UTF-8 output encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to sys.path so 'src' module can be imported
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.job_runner import run_job_execution

def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] != "-":
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                job_data = json.load(f)
        else:
            raw_input = sys.stdin.read().strip()
            if not raw_input:
                print(json.dumps({"status": "error", "message": "No JSON payload provided"}))
                sys.exit(1)
            job_data = json.loads(raw_input)

        result = run_job_execution(job_data)
        print("\n__NESTING_RESULT_START__")
        print(json.dumps(result, ensure_ascii=False))
        print("__NESTING_RESULT_END__")
    except Exception as e:
        err_msg = f"CLI Execution Error: {e}\n{traceback.format_exc()}"
        print(err_msg, file=sys.stderr)
        print("\n__NESTING_RESULT_START__")
        print(json.dumps({"status": "error", "message": str(e), "traceback": traceback.format_exc()}, ensure_ascii=False))
        print("__NESTING_RESULT_END__")
        sys.exit(1)

if __name__ == "__main__":
    main()
