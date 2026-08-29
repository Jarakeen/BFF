from pathlib import Path

# PyInstaller defines SPECPATH as the directory containing this spec file.
# packaging/ lives directly under the project root, so one parent is enough.
project_root = Path(SPECPATH).resolve().parent

# Read-only UI resources are bundled into PyInstaller's extraction directory.
# Writable application data (especially data/eso.db) is deliberately NOT
# bundled; the build scripts place it beside BFF.exe where engine.config finds it.
datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / "bff.ico"), "."),
]

a = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BFF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "bff.ico"),
)
