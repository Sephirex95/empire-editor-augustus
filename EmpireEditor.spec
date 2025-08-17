# -*- mode: python ; coding: utf-8 -*-

import inspect
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

app_name   = "EmpireEditor"
entry_file = "main_window.py"
icon_file  = "editor.ico"

excludes = [
    "numpy",
    "numpy.core",
    "numpy.random",
    "numpy.linalg",
    "mkl",
    "mkl_service",
]

# With contents_directory="_internal", destination "." means "_internal/"
# and "augustus_assets" means "_internal/augustus_assets/"
datas = [
    (icon_file, "."),                 # -> _internal/editor.ico
    ("augustus_assets", "augustus_assets"),  # -> _internal/augustus_assets/ (recursive)
]

block_cipher = None

a = Analysis(
    [entry_file],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,      # windowed app
    icon=icon_file,     # Explorer icon
)

collect_kwargs = dict(
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

# Put everything under _internal/ (PyInstaller >= 6.3)
if "contents_directory" in inspect.signature(COLLECT).parameters:
    collect_kwargs["contents_directory"] = "_internal"

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    **collect_kwargs
)
