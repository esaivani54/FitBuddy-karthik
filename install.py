"""
FitBuddy Windows Installer Script
Sets up Python virtual environment, installs dependencies, and prepares configuration.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / "venv"
PYTHON_EXE = sys.executable

def run_command(cmd, desc="Running step..."):
    print(f"[FitBuddy Setup] {desc}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"[FitBuddy Setup Error] Command failed: {' '.join(cmd)}")
        sys.exit(res.returncode)

def main():
    os.chdir(BASE_DIR)
    print("=" * 65)
    print(" ⚡ FITBUDDY — Windows Environment Setup & Requirements Installer")
    print("=" * 65)

    # 1. Create venv if not existing
    if not VENV_DIR.exists():
        run_command([PYTHON_EXE, "-m", "venv", "venv"], "Creating Python virtual environment (venv)...")
    else:
        print("[FitBuddy Setup] Existing virtual environment found.")

    venv_python = VENV_DIR / "Scripts" / "python.exe"
    venv_pip = VENV_DIR / "Scripts" / "pip.exe"
    
    installer_python = str(venv_python) if venv_python.exists() else PYTHON_EXE
    installer_pip = str(venv_pip) if venv_pip.exists() else "pip"

    # 2. Upgrade pip
    run_command([installer_python, "-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip package manager...")

    # 3. Install requirements
    req_file = BASE_DIR / "requirements.txt"
    if req_file.exists():
        run_command([installer_python, "-m", "pip", "install", "-r", "requirements.txt"], "Installing production dependencies from requirements.txt...")
    else:
        print("[FitBuddy Setup Error] requirements.txt not found!")
        sys.exit(1)

    # 4. Copy .env if not existing
    env_file = BASE_DIR / ".env"
    example_file = BASE_DIR / ".env.example"
    if not env_file.exists() and example_file.exists():
        print("[FitBuddy Setup] Creating .env from .env.example...")
        shutil.copy(example_file, env_file)

    # 5. Initialize Database if not already present
    db_file = BASE_DIR / "fitbuddy.db"
    if not db_file.exists():
        print("[FitBuddy Setup] Initializing new SQLite database (fitbuddy.db)...")
        init_script = (
            "from app.database import engine, Base; "
            "Base.metadata.create_all(bind=engine); "
            "print('[FitBuddy Setup] Database schema tables initialized cleanly.')"
        )
        run_command([installer_python, "-c", init_script], "Creating database schemas...")
    else:
        print("[FitBuddy Setup] Existing database (fitbuddy.db) detected.")

    print("\n" + "=" * 65)
    print(" ✅ FitBuddy environment setup is complete!")
    print(" To launch the application on Windows, run:")
    print("   python start.py")
    print("=" * 65)

if __name__ == "__main__":
    main()
