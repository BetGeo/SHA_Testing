"""Path helpers that work both as a plain script and as a PyInstaller bundle."""
import sys
from pathlib import Path


def bundle_dir() -> Path:
    """Where read-only bundled data (project_codes.tsv, ...) lives."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def app_dir() -> Path:
    """Where writable, user-editable files (config.yaml) should live —
    next to the .exe itself, not inside the temp bundle, so it survives
    between runs and is easy to find/edit."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent
