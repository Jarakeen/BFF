from pathlib import Path
import runpy

from PyInstaller.building.splash import Splash

# PyInstaller defines SPECPATH as the directory containing this spec file.
# packaging/ lives directly under the project root, so one parent is enough.
project_root = Path(SPECPATH).resolve().parent
manifest = runpy.run_path(str(project_root / "packaging" / "release_manifest.py"))
datas = manifest["pyinstaller_datas"](project_root)

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

# Runtime resources are supplied only by packaging/release_manifest.py. Do not
# replace this with a whole-tree assets copy: the source repo intentionally keeps
# retired themes, research art, and development-only files that must not ship.
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
