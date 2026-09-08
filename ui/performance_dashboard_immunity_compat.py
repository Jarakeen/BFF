from __future__ import annotations

"""Compatibility shims for the polished ESO Logs performance dashboard.

The canonical PerformanceDashboard persistence path has acquired a couple of
widget-level expectations that the cleaned dashboard intentionally presents in
a different way:

* ``exclude_downtime_toggle`` is the canonical attribute name for the visible
  boss-immunity toggle;
* ``tracked_effects_list`` is still used by saved-profile load/model plumbing,
  while the polished page presents tracked effects through a picker, summary
  rows, and graph-effect controls.

Keep those canonical attributes available without putting the old controls back
on screen.  This lets older/newer persistence code coexist with the cleaned UI
instead of crashing during CapabilitiesPage construction.
"""

from PySide6.QtWidgets import QListWidget

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    original_load = PerformanceDashboard.load

    def load_with_compat_aliases(self, profile):
        if not hasattr(self, "exclude_downtime_toggle"):
            toggle = getattr(self, "immunity_toggle", None)
            if toggle is not None:
                self.exclude_downtime_toggle = toggle

        # Newer canonical persistence calls set_tracked_effect_names(), whose
        # implementation still writes through this QListWidget.  The polished
        # dashboard no longer displays that legacy list, but the object must
        # remain available as an internal persistence adapter.
        if not hasattr(self, "tracked_effects_list"):
            legacy_list = QListWidget(self)
            legacy_list.hide()
            self.tracked_effects_list = legacy_list

        result = original_load(self, profile)

        # Keep the polished dashboard's actual tracked-effect state aligned with
        # a profile that carries the newer TrackedEffectNames field.  Limit to
        # the dashboard's intended selection count rather than silently reviving
        # an arbitrarily large legacy list.
        profile_names = getattr(profile, "TrackedEffectNames", None)
        if profile_names:
            names = []
            seen = set()
            for raw_name in profile_names:
                name = str(raw_name or "").strip()
                key = name.casefold()
                if not name or key in seen:
                    continue
                seen.add(key)
                names.append(name)
                if len(names) >= 8:
                    break
            if names:
                self._tracked_effect_names = names
                try:
                    from ui.performance_dashboard_polish_support import (
                        _render_tracked_effects,
                        _render_tracking_label,
                    )

                    _render_tracking_label(self)
                    _render_tracked_effects(self)
                except (AttributeError, RuntimeError):
                    # The adapter must never make profile loading less robust if
                    # a future dashboard layer changes presentation details.
                    pass

        return result

    PerformanceDashboard.load = load_with_compat_aliases
    _INSTALLED = True
