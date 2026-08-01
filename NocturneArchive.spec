# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root = Path(SPECPATH)
icon = root / "assets" / "NocturneArchive-V.ico"
a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "web"), "web"), (str(root / "assets"), "assets")],
    hiddenimports=[
        "PySide6.QtTest", "PySide6.QtWebChannel", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "nocturne_archive.pdf_store",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="NocturneArchive",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None, icon=str(icon),
)
