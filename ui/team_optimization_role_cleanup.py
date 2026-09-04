from __future__ import annotations


_INSTALLED = False
_ORIGINAL_INIT = None


def _remove_combo_text(combo, text: str) -> None:
    index = combo.findText(text)
    if index >= 0:
        combo.removeItem(index)


def _refocus_optimization_ui(page) -> None:
    """Remove composition/prescription controls from the Optimization surface.

    Composition creation is moving upstream to Comp Builder. Optimization remains
    responsible for auditing, improving, and comparing teams that already exist.
    The prescription services stay installed because Comp Builder and roster
    optimization can reuse that tested machinery without exposing it here.
    """

    page.header.title.setText("Team Optimization")
    page.header.subtitle.setText(
        "Audit, improve, and compare an existing team. Composition creation lives in Comp Builder."
    )
    page.header.department.setText("RAID ENGINE • OPTIMIZATION")

    # Keep Audit / Optimize / Compare. Recruitment planning belongs to Comp Builder.
    for index in range(page.mode_tabs.count() - 1, -1, -1):
        title = page.mode_tabs.tabText(index)
        if title == "Recruitment Plan":
            page.mode_tabs.removeTab(index)
        elif title == "Build Best Team":
            page.mode_tabs.setTabText(index, "Optimize Team")

    # The old action generated a new composition/prescription from scratch. That is
    # precisely the responsibility being moved out of this page.
    if hasattr(page, "generate_button"):
        page.generate_button.hide()
        page.generate_button.setEnabled(False)

    # Prescription preview and prescribed-build promotion are orchestration UI for
    # the old flow. Keep the underlying widgets alive for installed compatibility
    # layers, but remove the card from the user's Optimization workspace.
    if hasattr(page, "change_card"):
        page.change_card.hide()
        page.change_card.setMaximumHeight(0)

    # Recruitment-only source is composition planning rather than optimization.
    if hasattr(page, "team_source_combo"):
        _remove_combo_text(page.team_source_combo, "Recruitment Plan Only")

    # Existing-team optimization may still include open recruit chairs, so Hybrid
    # remains available alongside Saved Players Only.
    page.current_prescription = None
    page.status.info(
        f"Optimization ready • {len(page.roster.Members)} saved build(s) available. "
        "Use this page to audit, improve, or compare an existing team."
    )


def _init_refocused(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)
    _refocus_optimization_ui(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    _ORIGINAL_INIT = OptimizationPage.__init__
    OptimizationPage.__init__ = _init_refocused
    _INSTALLED = True
