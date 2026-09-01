from __future__ import annotations

import os


_FALSE_VALUES = {"0", "false", "no", "off", "disabled"}
_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}


def broadcast_enabled() -> bool:
    """Return whether the optional Broadcast module is enabled.

    Broadcast remains enabled by default for backwards compatibility. The
    environment override exists so the core application can be exercised with
    Broadcast completely absent before packaging/install controls are added.
    """

    raw = os.environ.get("BFF_BROADCAST_ENABLED", "1").strip().lower()
    if raw in _FALSE_VALUES:
        return False
    if raw in _TRUE_VALUES:
        return True
    return True
