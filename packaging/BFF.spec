from pathlib import Path

from PyInstaller.building.splash import Splash

# PyInstaller defines SPECPATH as the directory containing this spec file.
# packaging/ lives directly under the project root, so one parent is enough.
project_root = Path(SPECPATH).resolve().parent

# Build a deliberately dark, static boot plate for the PyInstaller bootloader.
# This appears before Python/Qt has finished starting, preventing the one-file
# executable from presenting a bright/blank startup flash. It contains no
# animation, blinking, cycling text, or progress effects.
boot_splash_path = project_root / "build" / "foundrydock_boot_splash.ppm"
boot_splash_path.parent.mkdir(parents=True, exist_ok=True)

width, height = 680, 400
background = (12, 23, 27)       # #0C171B
outer_border = (92, 78, 52)     # subdued brass, intentionally low-luminance
inner_border = (31, 63, 69)     # muted teal

pixels = bytearray()
for y in range(height):
    for x in range(width):
        if x in (12, 13, width - 14, width - 13) or y in (12, 13, height - 14, height - 13):
            pixels.extend(outer_border)
        elif x in (20, width - 21) or y in (20, height - 21):
            pixels.extend(inner_border)
        else:
            pixels.extend(background)

with boot_splash_path.open("wb") as handle:
    handle.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
    handle.write(pixels)

# Read-only UI resources are bundled into PyInstaller's extraction directory.
# Writable application data (especially data/eso.db) is deliberately NOT
# bundled; the build scripts place it beside FoundryDock.exe where engine.config finds it.
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

boot_splash = Splash(
    str(boot_splash_path),
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    boot_splash,
    boot_splash.binaries,
    a.binaries,
    a.datas,
    [],
    name="FoundryDock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
