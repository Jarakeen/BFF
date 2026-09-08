from __future__ import annotations

"""Compatibility shim for the polished ESO Logs performance dashboard.

The canonical PerformanceDashboard load path now expects an
``exclude_downtime_toggle`` control.  The polished dashboard intentionally
renamed the visible control to ``immunity_toggle``.  Keep both attribute names
pointing at the same checkbox so saved performance profiles can load before the
Capabilities page finishes constructing.
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    original_load = PerformanceDashboard.load

    def load_with_immunity_alias(self, profile):
        if not hasattr(self, "exclude_downtime_toggle"):
            toggle = getattr(self, "immunity_toggle", None)
            if toggle is not None:
                self.exclude_downtime_toggle = toggle
        return original_load(self, profile)

    PerformanceDashboard.load = load_with_immunity_alias
    _INSTALLED = True
