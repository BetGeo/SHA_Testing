# Build with:  pyinstaller voice_timesheet.spec
# Produces a single windowed executable with no console window.
# Must be run ON the target OS — PyInstaller does not cross-compile
# (build on Windows to get a .exe, on macOS to get a .app/binary).
import sys
from pathlib import Path

block_cipher = None
here = Path(SPECPATH)

a = Analysis(
    ["gui.py"],
    pathex=[str(here)],
    binaries=[],
    datas=[
        (str(here / "data" / "project_codes.tsv"), "data"),
    ],
    hiddenimports=["speech_recognition", "yaml"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SperlingHansenVoiceTimesheet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,   # GUI app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
