# engine/config.py
"""Shared runtime paths.

Every page was resolving `data/` a different way -- some checked
`sys.frozen` (correct once packaged into an exe), some used
`Path(__file__).resolve().parents[1]` (breaks once frozen, because
`__file__` resolves inside PyInstaller's temp extraction folder, not
next to the exe), and one hardcoded a bare relative path (breaks
depending on the working directory the exe was launched from).

Everything should go through get_data_dir() instead so there's one
place this logic lives.
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_app_root() -> Path:
    """Directory the running app lives in.

    When frozen by PyInstaller, this is the folder containing the
    .exe -- NOT the temporary _MEIPASS extraction folder -- so that
    files placed next to the exe (like data/eso.db) are found
    reliably regardless of --onefile vs --onedir or where the exe
    was launched from.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


def get_data_dir() -> Path:
    return get_app_root() / "data"


def get_resource_path(*parts: str) -> Path:
    """Path to a bundled read-only resource (icon, stylesheet, etc).

    Unlike get_data_dir(), this does NOT point next to the exe.
    PyInstaller unpacks bundled `datas` into a temp folder
    (`sys._MEIPASS`) at launch, so bundled assets have to be looked
    up there when frozen -- using get_app_root() here would silently
    fail to find them.
    """

    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", get_app_root()))
    else:
        base = get_app_root()

    return base.joinpath(*parts)


DEFAULT_DATABASE = get_data_dir() / "eso.db"