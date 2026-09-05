from __future__ import annotations

_INSTALLED = False
_ORIGINAL_BUILD_UI = None


def _install_navigation() -> None:
    from ui.components import foundry_sidebar
    from ui import ux_icons

    for section in foundry_sidebar.CORE_NAV_SECTIONS:
        if not isinstance(section, dict) or section.get("label") != "Tool":
            continue
        children = section.setdefault("children", [])
        route = ("Scribing Simulator", "scribing_simulator")
        if route not in children:
            # Keep the simulator beside the other data/theorycrafting tools.
            insert_at = 1 if children else 0
            children.insert(insert_at, route)
        break

    ux_icons._EXACT.setdefault("scribing simulator", "lunar-wand")


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI
    if _INSTALLED:
        return

    _install_navigation()

    from ui.main_window import MainWindow
    from ui.scribing_simulator_page import ScribingSimulatorPage

    _ORIGINAL_BUILD_UI = MainWindow.build_ui

    def build_ui_with_scribing_simulator(self) -> None:
        _ORIGINAL_BUILD_UI(self)
        if "scribing_simulator" in self.pages:
            return

        page = ScribingSimulatorPage()
        container = self.wrap_page(page)
        self.pages["scribing_simulator"] = page
        self.page_containers["scribing_simulator"] = container
        self.stack.addWidget(container)

    MainWindow.build_ui = build_ui_with_scribing_simulator
    _INSTALLED = True
