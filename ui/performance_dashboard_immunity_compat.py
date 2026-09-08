from __future__ import annotations

"""Compatibility shims for the polished ESO Logs performance dashboard.

The canonical PerformanceDashboard persistence path has acquired a couple of
widget-level expectations that the cleaned dashboard intentionally presents in
a different way:

* ``exclude_downtime_toggle`` is the canonical attribute name for the visible
  boss-immunity toggle;
* ``tracked_effects_list`` is still used by saved-profile/model plumbing, while
  the polished page presents tracked effects through a picker, summary rows,
  and graph-effect controls.

These adapters must exist immediately after dashboard construction, not only
when a saved profile is loaded. CapabilitiesPage reads ``dashboard.model`` while
creating a brand-new member tab, before ``load()`` has necessarily run.
"""

from PySide6.QtWidgets import QListWidget

_INSTALLED = False


def _ensure_compat_aliases(widget) -> None:
    if not hasattr(widget, "exclude_downtime_toggle"):
        toggle = getattr(widget, "immunity_toggle", None)
        if toggle is not None:
            widget.exclude_downtime_toggle = toggle

    # Canonical model/tracked_effect_names still reads this QListWidget. The
    # polished dashboard no longer shows the legacy control, so keep it as a
    # hidden persistence adapter that exists for the entire widget lifetime.
    if not hasattr(widget, "tracked_effects_list"):
        legacy_list = QListWidget(widget)
        legacy_list.hide()
        widget.tracked_effects_list = legacy_list


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    original_build_ui = PerformanceDashboard.build_ui
    original_load = PerformanceDashboard.load

    def build_ui_with_compat_aliases(self):
        result = original_build_ui(self)
        _ensure_compat_aliases(self)
        return result

    def load_with_compat_aliases(self, profile):
        _ensure_compat_aliases(self)
        result = original_load(self, profile)

        # Keep the polished dashboard's actual tracked-effect state aligned with
        # a profile that carries the newer TrackedEffectNames field. Limit to
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

    PerformanceDashboard.build_ui = build_ui_with_compat_aliases
    PerformanceDashboard.load = load_with_compat_aliases
    _INSTALLED = True
