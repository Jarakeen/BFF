from __future__ import annotations

"""Install the Extreme Build Lab as a Tools page without expanding MainWindow."""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services.extreme_complete_blueprint_service import ExtremeCompleteBlueprintService
    from ui import main_window
    from ui.extreme_specialized_optimization_page import ExtremeSpecializedOptimizationPage

    original_build_ui = main_window.MainWindow.build_ui

    def build_ui_with_extreme_lab(self) -> None:
        original_build_ui(self)
        if "extreme_optimization" in self.pages:
            return

        page = ExtremeSpecializedOptimizationPage()
        # The page owns the canonical 32-record catalog and both shared-static and
        # specialized execution gateways. This installer only supplies the completed
        # from-scratch blueprint layer; it must not append or reclassify objectives.
        page.blueprint_service = ExtremeCompleteBlueprintService()
        self.pages["extreme_optimization"] = page
        container = self.wrap_page(page)
        self.page_containers["extreme_optimization"] = container
        self.stack.addWidget(container)

    main_window.MainWindow.build_ui = build_ui_with_extreme_lab
    _INSTALLED = True
