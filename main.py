import os
import sys
import time
import subprocess
import webbrowser
import requests

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def print_banner():
    print("=" * 65)
    print(" AUTONOMOUS PHYSICAL CHARACTERIZATION SYSTEM - DEBUG MODE")
    print(" Hardware: Ossila SMU (COM3) | Dual AI Engine | Streamlit Dashboard")
    print("=" * 65)


def check_backend_alive(url="http://127.0.0.1:8000/", timeout_sec=10):
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    print_banner()

    # 1. Start FastAPI Backend in background process (with LIVE terminal output)
    print("\n[1/3] Starting FastAPI Backend Service (port 8000)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
    )

    if not check_backend_alive():
        print("❌ Error: FastAPI backend failed to launch.")
        backend_proc.terminate()
        sys.exit(1)

    print("✅ Backend API is ONLINE at http://127.0.0.1:8000")

    # 2. Launch Streamlit UI
    print("\n[2/3] Launching Streamlit UI Dashboard...")
    frontend_cmd = [sys.executable, "-m", "streamlit", "run", os.path.join(ROOT_DIR, "frontend", "app.py")]

    print("\n[3/3] System is LIVE! Press Ctrl+C in terminal to safely terminate.")
    print("=" * 65)

    try:
        time.sleep(1.5)
        webbrowser.open("http://localhost:8501")
        subprocess.run(frontend_cmd)
    except KeyboardInterrupt:
        print("\n\nShutting down Autonomous Lab system...")
    finally:
        backend_proc.terminate()
        print("✅ Backend and Hardware connection safely closed.")


if __name__ == "__main__":
    main()