from __future__ import annotations

import os

from services.paths import BROADCAST_MODULE


_FALSE_VALUES = {"0", "false", "no", "off", "disabled"}
_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
_BROADCAST_MANIFEST = BROADCAST_MODULE / "manifest.json"


def broadcast_installed() -> bool:
    """Return whether the optional Broadcast module payload is installed."""

    return _BROADCAST_MANIFEST.is_file()


def broadcast_enabled() -> bool:
    """Return whether the installed optional Broadcast module is enabled.

    Broadcast stays installed but is disabled by default. Set the environment
    override explicitly to a true value to re-enable it. A missing Broadcast
    manifest always wins and keeps the module disabled.
    """

    if not broadcast_installed():
        return False

    raw = os.environ.get("BFF_BROADCAST_ENABLED", "0").strip().lower()
    if raw in _FALSE_VALUES:
        return False
    if raw in _TRUE_VALUES:
        return True
    return False
