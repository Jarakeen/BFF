from __future__ import annotations

from PySide6.QtWidgets import QLabel


_INSTALLED = False
_ORIGINAL_ROSTER_INIT = None
_ORIGINAL_REFRESH_CHOICES = None


def _current_generated_plan_name(page) -> str:
    combo = getattr(page, "generated_plan_combo", None)
    if combo is not None:
        name = combo.currentText().strip()
        if name:
            return name
    service = getattr(page, "generated_plan_service", None)
    if service is not None:
        plan = service.latest_plan()
        if plan is not None:
            return plan.name
    return "No generated team loaded"


def _refresh_plan_name_label(page) -> None:
    label = getattr(page, "generated_plan_name_label", None)
    if label is not None:
        label.setText(f"TEAM: {_current_generated_plan_name(page)}")


def _roster_init_without_generated_dropdown(self, parent=None) -> None:
    assert _ORIGINAL_ROSTER_INIT is not None
    _ORIGINAL_ROSTER_INIT(self, parent)

    combo = getattr(self, "generated_plan_combo", None)
    if combo is not None:
        host = combo.parentWidget()
        if host is not None:
            host.hide()
        else:
            combo.hide()

    self.generated_plan_name_label = QLabel()
    self.generated_plan_name_label.setProperty("generatedPlanName", True)
    self.header.add_context_widget(self.generated_plan_name_label)
    _refresh_plan_name_label(self)


def _refresh_generated_plan_choices_with_name(page, selected: str | None = None) -> None:
    assert _ORIGINAL_REFRESH_CHOICES is not None
    _ORIGINAL_REFRESH_CHOICES(page, selected)
    _refresh_plan_name_label(page)


def install() -> None:
    global _INSTALLED, _ORIGINAL_ROSTER_INIT, _ORIGINAL_REFRESH_CHOICES
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    _ORIGINAL_ROSTER_INIT = RosterPage.__init__
    _ORIGINAL_REFRESH_CHOICES = RosterPage._refresh_generated_plan_choices
    RosterPage.__init__ = _roster_init_without_generated_dropdown
    RosterPage._refresh_generated_plan_choices = _refresh_generated_plan_choices_with_name
    _INSTALLED = True
