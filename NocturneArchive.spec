# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root = Path(SPECPATH)
a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=["PySide6.QtWebEngineCore","PySide6.QtWebEngineWidgets"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="NocturneArchive",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False,
    icon=str(root / "assets" / "NocturneArchive-V.ico"),
)
