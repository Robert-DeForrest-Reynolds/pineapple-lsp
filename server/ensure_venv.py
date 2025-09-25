import os
import subprocess
import sys
from pathlib import Path
import venv

# Choose the venv location (relative to this script)
VENV_DIR = Path(__file__).parent / ".venv"

def ensure_venv():
    python_exe = sys.executable
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)
    
    # Determine the Python executable inside the venv
    if os.name == "nt":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    # Install dependencies if not present
    try:
        import pygls
    except ImportError:
        print("Installing dependencies in venv...")
        subprocess.check_call([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([str(venv_python), "-m", "pip", "install", "pygls", "attrs", "lsprotocol"])

    return venv_python

# Call this at startup
VENV_PYTHON = ensure_venv()