from __future__ import annotations

"""Explicit application composition for Performance Dashboard surface extensions.

The ordered decorators in this module must be installed before the Build Editor
performance layer and before MainWindow construction. Feature modules retain
only their own behavior.
"""


_BOOTSTRAPPED = False


def bootstrap_performance_dashboard_extensions() -> None:
    """Install Performance Dashboard and related focus extensions exactly once."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from ui.performance_dashboard_polish_support import install as install_performance_dashboard_polish
    install_performance_dashboard_polish()
    from ui.performance_dashboard_overlay_support import install as install_performance_dashboard_overlay
    install_performance_dashboard_overlay()
    from ui.performance_dashboard_timeline_support import install as install_performance_dashboard_timeline
    install_performance_dashboard_timeline()
    from ui.performance_dashboard_immunity_compat import install as install_performance_dashboard_immunity_compat
    install_performance_dashboard_immunity_compat()
    from ui.performance_dashboard_effect_retrieval_support import install as install_performance_dashboard_effect_retrieval
    install_performance_dashboard_effect_retrieval()
    from ui.performance_dashboard_timeline_service_support import install as install_performance_dashboard_timeline_service
    install_performance_dashboard_timeline_service()
    from ui.performance_dashboard_boss_activity_support import install as install_performance_dashboard_boss_activity
    install_performance_dashboard_boss_activity()
    from ui.performance_dashboard_focus_support import install as install_performance_dashboard_focus
    install_performance_dashboard_focus()
    from ui.operations_console_focus_support import install as install_operations_console_focus
    install_operations_console_focus()

    _BOOTSTRAPPED = True


__all__ = ["bootstrap_performance_dashboard_extensions"]
