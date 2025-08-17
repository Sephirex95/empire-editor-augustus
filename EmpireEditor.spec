# EmpireEditor.spec
# -*- mode: python ; coding: utf-8 -*-

import inspect
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree

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

# Put editor.ico inside _internal so your app can load it at runtime.
datas = [
    ('editor.ico', '.'),
    ('augustus_assets', 'augustus_assets')
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
    console=False,        # windowed app
    icon=icon_file,       # EXE icon in Explorer
)

# Use contents_directory if available (PyInstaller ≥ 6.3) so deps go under _internal/
collect_kwargs = dict(
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)
supports_contents_dir = "contents_directory" in inspect.signature(COLLECT).parameters
if supports_contents_dir:
    collect_kwargs["contents_directory"] = "_internal"

# IMPORTANT: With contents_directory, do NOT prefix Tree with "_internal/..."
# We want _internal/augustus_assets, not _internal/_internal/augustus_assets
assets_tree = Tree(
    "augustus_assets",
    prefix=("augustus_assets" if supports_contents_dir else "_internal/augustus_assets")
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    assets_tree,
    **collect_kwargs
)
