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

import os
import shutil
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


def get_settings_path() -> Path:
    """Canonical FoundryDock settings file beside the source tree or packaged EXE."""
    return get_app_root() / "settings.json"


def get_user_data_dir() -> Path:
    """Writable FoundryDock state, separate from replaceable app/reference data.

    Source runs keep user state inside the repository user_data folder. Frozen
    builds use LOCALAPPDATA by default so replacing or moving an EXE cannot
    overwrite the user's roster/progress. FOUNDRYDOCK_USER_DATA_DIR is an
    explicit escape hatch for portable/test builds and prepared workspaces.
    """

    override = str(os.environ.get("FOUNDRYDOCK_USER_DATA_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        local = str(os.environ.get("LOCALAPPDATA", "") or "").strip()
        if local:
            return Path(local) / "FoundryDock"
        return Path.home() / "AppData" / "Local" / "FoundryDock"

    return get_app_root() / "user_data"


def get_user_database_path() -> Path:
    return get_user_data_dir() / "foundrydock.db"


def ensure_user_database() -> Path:
    """Provision the user-owned database without replacing an existing one.

    Frozen builds may optionally bundle _seed_user_data/foundrydock.db. The
    seed is copied only on first run, which supports prepared EXEs while
    preserving every later local modification.
    """

    target = get_user_database_path()
    if target.is_file():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    if getattr(sys, "frozen", False):
        seed = get_resource_path("_seed_user_data", "foundrydock.db")
        if seed.is_file():
            shutil.copy2(seed, target)
            return target

    target.touch(exist_ok=True)
    return target


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


def ensure_default_database() -> Path:
    """Ensure a frozen install has its external canonical ESO database.

    Friend builds normally ship ``data/eso.db`` beside the executable.  A user
    can still accidentally separate the EXE from that folder, so frozen builds
    also contain a read-only seed copy under ``_seed_data``.  Provision that
    seed only when the external database is missing.  Existing databases are
    never replaced, which keeps updater runs from overwriting user state.

    Source/development runs deliberately do not provision anything; their
    checked-out ``data/eso.db`` remains authoritative.
    """

    target = get_data_dir() / "eso.db"
    if target.is_file() or not getattr(sys, "frozen", False):
        return target

    seed = get_resource_path("_seed_data", "eso.db")
    if not seed.is_file():
        raise FileNotFoundError(
            f"FoundryDock database is missing at {target} and the bundled seed "
            f"database is unavailable at {seed}."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(seed, target)
    return target


DEFAULT_DATABASE = get_data_dir() / "eso.db"