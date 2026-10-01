"""
FitBuddy Linux Startup Script
Checks database initialization, finds an available port (auto fallback), starts Uvicorn, and opens browser.
"""

import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8000

def is_port_available(host: str, port: int) -> bool:
    """Check if a specific TCP port is free for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False

def find_available_port(host: str = "127.0.0.1", start_port: int = 8000, max_attempts: int = 100) -> int:
    """Finds the first available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(host, port):
            if port != start_port:
                print(f"[FitBuddy] Notice: Port {start_port} is already in use. Automatically falling back to port {port}...")
            return port
    
    # Fallback to system-assigned ephemeral port if range exhausted
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        assigned_port = s.getsockname()[1]
        print(f"[FitBuddy] Notice: Port {start_port} in use. Assigned port {assigned_port} by OS.")
        return assigned_port

def get_python_executable():
    """Locate the Python executable in Linux venv or fallback to system python3."""
    venv_python = BASE_DIR / "venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def ensure_env_file():
    """Ensure .env exists by copying .env.example if necessary."""
    env_file = BASE_DIR / ".env"
    example_file = BASE_DIR / ".env.example"
    if not env_file.exists() and example_file.exists():
        print("[FitBuddy] Creating .env from .env.example...")
        env_file.write_text(example_file.read_text(encoding="utf-8"), encoding="utf-8")

def check_and_init_database():
    """Initializes SQLite database schema tables cleanly."""
    print("[FitBuddy] Checking database initialization...")
    try:
        from app.database import engine, Base
        Base.metadata.create_all(bind=engine)
        print("[FitBuddy] Database tables verified successfully.")
    except Exception as e:
        print(f"[FitBuddy Warning] Database check encountered: {e}")

def open_browser_delayed(app_url: str, delay=1.5):
    """Wait for Uvicorn to bind and launch the default web browser."""
    time.sleep(delay)
    print(f"[FitBuddy] Launching browser at {app_url} ...")
    try:
        opened = webbrowser.open(app_url, new=2)
        if not opened:
            subprocess.run(["xdg-open", app_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[FitBuddy] Notice: Please open {app_url} in your browser.")

def ensure_venv_execution():
    """Ensure the script runs inside the virtual environment if available."""
    venv_python = BASE_DIR / "venv" / "bin" / "python3"
    if venv_python.exists():
        current_exe = Path(sys.executable).resolve()
        target_exe = venv_python.resolve()
        if current_exe != target_exe:
            os.execv(str(target_exe), [str(target_exe)] + sys.argv)

def main():
    ensure_venv_execution()
    os.chdir(BASE_DIR)
    ensure_env_file()
    check_and_init_database()

    # Determine free port
    port = find_available_port(HOST, DEFAULT_PORT)
    app_url = f"http://localhost:{port}"

    print("=" * 65)
    print(" ⚡ FITBUDDY — AI Fitness Planning & Nutrition Platform (Linux)")
    print(f" Web UI & Dashboard: {app_url}")
    print(f" API Documentation:  {app_url}/docs")
    print("=" * 65)
    print(f"[FitBuddy] Starting Uvicorn ASGI Server on port {port}... (Press Ctrl+C to stop)")

    # Launch browser in a background thread
    threading.Thread(target=open_browser_delayed, args=(app_url, 1.5), daemon=True).start()

    # Run Uvicorn server
    try:
        import uvicorn
        uvicorn.run("app.main:app", host=HOST, port=port, reload=True)
    except ImportError:
        python_exe = get_python_executable()
        subprocess.run([python_exe, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(port), "--reload"])

if __name__ == "__main__":
    main()
