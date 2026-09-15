from __future__ import annotations

"""Explicit application composition for Extreme Build Lab UI extensions.

This module owns the ordered profile, blueprint-result, and record-card
installers required before the Extreme Build Lab page is attached to MainWindow.
The Extreme page feature retains its own service and navigation behavior.
"""


_BOOTSTRAPPED = False


def bootstrap_extreme_optimization_extensions() -> None:
    """Install the Extreme Build Lab extension graph exactly once."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from ui.extreme_critical_profile_support import install as install_extreme_critical_profile_support
    from ui.extreme_class_configuration_support import install as install_extreme_class_configuration_support
    from ui.extreme_blueprint_result_support import install as install_extreme_blueprint_result_support
    from ui.extreme_health_recovery_record_support import install as install_extreme_health_recovery_record_support
    from ui.extreme_magicka_recovery_record_support import install as install_extreme_magicka_recovery_record_support
    from ui.extreme_stamina_recovery_record_support import install as install_extreme_stamina_recovery_record_support
    from ui.extreme_max_health_record_support import install as install_extreme_max_health_record_support
    from ui.extreme_max_magicka_record_support import install as install_extreme_max_magicka_record_support
    from ui.extreme_max_stamina_record_support import install as install_extreme_max_stamina_record_support

    install_extreme_critical_profile_support()
    install_extreme_class_configuration_support()
    install_extreme_blueprint_result_support()
    install_extreme_max_magicka_record_support()
    install_extreme_max_health_record_support()
    install_extreme_max_stamina_record_support()
    install_extreme_health_recovery_record_support()
    install_extreme_magicka_recovery_record_support()
    install_extreme_stamina_recovery_record_support()

    _BOOTSTRAPPED = True


__all__ = ["bootstrap_extreme_optimization_extensions"]
