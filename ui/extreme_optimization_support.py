from __future__ import annotations

"""Install the Extreme Build Lab as a Tools page without expanding MainWindow."""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services.extreme_complete_blueprint_service import ExtremeCompleteBlueprintService
    from ui import main_window
    from ui.extreme_critical_profile_support import install as install_extreme_critical_profile_support
    from ui.extreme_class_configuration_support import install as install_extreme_class_configuration_support
    from ui.extreme_optimization_page import ExtremeOptimizationPage

    install_extreme_critical_profile_support()
    install_extreme_class_configuration_support()
    original_build_ui = main_window.MainWindow.build_ui

    def build_ui_with_extreme_lab(self) -> None:
        original_build_ui(self)
        if "extreme_optimization" in self.pages:
            return

        page = ExtremeOptimizationPage()
        # The page still owns the same public blueprint-service contract, but
        # from-scratch searches now use the systemic completion layer rather
        # than the earlier Spell-Damage-only profile implementation.
        page.blueprint_service = ExtremeCompleteBlueprintService()
        self.pages["extreme_optimization"] = page
        container = self.wrap_page(page)
        self.page_containers["extreme_optimization"] = container
        self.stack.addWidget(container)

    main_window.MainWindow.build_ui = build_ui_with_extreme_lab
    _INSTALLED = True
