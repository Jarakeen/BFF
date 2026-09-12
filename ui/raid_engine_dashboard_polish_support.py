from __future__ import annotations

"""Visual polish and focused workflow tweaks for Raid Engine surfaces."""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QWidget,
)

from engine.config import get_data_dir
from services.accessibility_preferences import VISUAL_THEME_RYLO
from ui.components.foundry_button import ButtonRole, FoundryButton


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_REFRESH_ACTIVE = None
_ORIGINAL_REFRESH_COVERAGE = None
_ORIGINAL_REFRESH_NEXT_ACTIONS = None
_ORIGINAL_BUILDS_BUILD_UI = None
_ORIGINAL_OVERVIEW_BUILD_UI = None
_ORIGINAL_OVERVIEW_PLAYER_CARD = None
_ORIGINAL_OVERVIEW_RAID_STATUS_CARD = None
_ORIGINAL_OVERVIEW_RAID_SCHEDULE_CARD = None
_ORIGINAL_OVERVIEW_SKILLS_CARD = None
_ORIGINAL_COVERAGE_TAB = None
_ORIGINAL_ENCOUNTERS_BUILD_UI = None


def _is_rylo() -> bool:
    app = QApplication.instance()
    return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)


def _status_palette(kind: str) -> tuple[str, str, str]:
    key = str(kind or "").strip().upper()
    if _is_rylo():
        if key in {"SAVED", "COVERED", "AVAILABLE"}:
            return "#193126", "#6DA07D", "#D7E8DC"
        if key in {"NEEDS BUILD", "MISSING", "NOT_FOUND"}:
            return "#3A1719", "#A73A40", "#E8C6C8"
        return "#25272B", "#696B70", "#D0C8B9"
    if key in {"SAVED", "COVERED", "AVAILABLE"}:
        return "#173A2B", "#4F8E68", "#D9EEE2"
    if key in {"NEEDS BUILD", "MISSING", "NOT_FOUND"}:
        return "#4A281B", "#B36A38", "#F0D8C2"
    return "#173339", "#4C777C", "#D6E6E5"


def _pill(text: str, kind: str) -> QLabel:
    background, border, foreground = _status_palette(kind)
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setMinimumHeight(22)
    label.setContentsMargins(9, 1, 9, 1)
    label.setStyleSheet(
        "QLabel {"
        f"background: {background}; color: {foreground}; border: 1px solid {border};"
        f"border-radius: {'0' if _is_rylo() else '10px'}; padding: 1px 8px; font-weight: 600;"
        "}"
    )
    return label


def _notes_path() -> Path:
    return get_data_dir() / "raid_engine_dashboard_notes.json"


def _note_key(page) -> str:
    trial = page.trial_combo.currentText().strip() or "Unknown Trial"
    difficulty = page.difficulty_combo.currentText().strip() or "Unknown Difficulty"
    plan = page.plan_combo.currentText().strip() or "Current Raid Composition"
    return " | ".join((trial, difficulty, plan))


def _load_notes() -> dict[str, str]:
    path = _notes_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if str(value).strip()}


def _save_notes(notes: dict[str, str]) -> None:
    path = _notes_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _save_next_actions(page) -> None:
    notes = _load_notes()
    key = _note_key(page)
    text = page.next_actions_editor.toPlainText().strip()
    if text:
        notes[key] = text
    else:
        notes.pop(key, None)
    try:
        _save_notes(notes)
    except OSError as exc:
        page.status.warning(f"Could not save Raid Engine notes: {exc}")
        return
    page._raid_engine_notes_dirty = False
    page.status.success("Next Actions note saved.")


def _replace_next_actions_editor(page) -> None:
    old = getattr(page, "next_actions_label", None)
    if old is not None:
        page.next_actions_card.body_layout.removeWidget(old)
        old.hide()
        old.deleteLater()

    editor = QTextEdit()
    editor.setPlaceholderText("Write raid notes, assignments, reminders, or next steps here...")
    editor.setMinimumHeight(150)
    editor.setAcceptRichText(False)
    editor.setProperty("raidEngineNextActionsEditor", True)
    page.next_actions_editor = editor
    page._raid_engine_notes_dirty = False
    editor.textChanged.connect(lambda: setattr(page, "_raid_engine_notes_dirty", True))

    # Insert before the existing stretch so the note fills the parchment card.
    page.next_actions_card.body_layout.insertWidget(0, editor, 1)
    save = FoundryButton("Save Note", role=ButtonRole.SECONDARY, compact=True)
    save.setToolTip("Save this note for the current trial, difficulty, and team/plan.")
    save.clicked.connect(lambda *_: _save_next_actions(page))
    page.next_actions_save_button = save
    page.next_actions_card.set_header_action(save)


def _take_widget_from_layout(layout, target: QWidget) -> bool:
    """Detach one widget from nested layouts without disturbing sibling content."""
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            layout.takeAt(index)
            return True
        nested = item.layout()
        if nested is not None and _take_widget_from_layout(nested, target):
            return True
    return False


def _center_create_character_button(page) -> None:
    """Give the creation entry point its own balanced header slot."""
    button = getattr(page, "create_character_button", None)
    header = getattr(page, "header", None)
    context_layout = getattr(header, "context_layout", None)
    if not isinstance(button, QPushButton) or context_layout is None:
        return

    _take_widget_from_layout(context_layout, button)
    button.setParent(None)
    host = QWidget(header)
    host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    row.addStretch(1)
    row.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
    row.addStretch(1)
    context_layout.insertWidget(0, host, 1, Qt.AlignmentFlag.AlignBottom)
    page.create_character_button_host = host


def _center_named_card_button(card, text: str) -> QPushButton | None:
    """Move one named action into a clean bottom-center row."""
    button = next(
        (candidate for candidate in card.body.findChildren(QPushButton) if candidate.text() == text),
        None,
    )
    if button is None:
        return None
    _take_widget_from_layout(card.body_layout, button)
    button.setParent(None)
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    row.addStretch(1)
    row.addWidget(button)
    row.addStretch(1)
    card.body_layout.addLayout(row)
    return button


def _show_page(source, page_name: str) -> None:
    window = source.window()
    show_page = getattr(window, "show_page", None)
    if callable(show_page):
        show_page(page_name)


def _open_coverage_tab(source, tab_name: str) -> None:
    """Open Coverage and select one of its canonical workspaces by label."""
    window = source.window()
    show_page = getattr(window, "show_page", None)
    if callable(show_page):
        show_page("console:7")
    coverage_page = getattr(window, "pages", {}).get("console:7")
    tabs = getattr(coverage_page, "tabs", None)
    if tabs is None:
        return
    wanted = tab_name.strip().upper()
    for index in range(tabs.count()):
        if tabs.tabText(index).strip().upper() == wanted:
            tabs.setCurrentIndex(index)
            break


def _open_coverage_raid_review(overview) -> None:
    """Navigate a focus/performance action directly to Coverage > Raid Review."""
    _open_coverage_tab(overview, "RAID REVIEW")


def _rewire_button(button: QPushButton, callback) -> None:
    """Replace an old dashboard shortcut with one explicit destination."""
    try:
        button.clicked.disconnect()
    except (RuntimeError, TypeError):
        pass
    button.clicked.connect(lambda *_: callback())


def _wire_dashboard_navigation(page) -> None:
    """Make Raid Engine shortcut labels land on the workspaces they name."""
    for button in page.findChildren(QPushButton):
        text = button.text().strip()
        if text == "Performance":
            _rewire_button(button, lambda: _open_coverage_tab(page, "RAID REVIEW"))
        elif text == "Coverage":
            _rewire_button(button, lambda: _open_coverage_tab(page, "BUFFS & DEBUFFS"))
        elif text.startswith("Browse All Saved Builds"):
            _rewire_button(button, lambda: _show_page(page, "characters"))


def _init_with_dashboard_polish(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)

    # Keep the composition art readable while giving the Active Composition
    # table enough width for full status pills and vertical breathing room.
    self.composition_ring.setMinimumSize(560, 350)
    self.composition_card.setMinimumWidth(575)
    self.active_card.setMinimumWidth(420)
    self.active_table.setMinimumWidth(405)
    self.active_table.setMinimumHeight(500)
    row_header = self.active_table.verticalHeader()
    row_header.setDefaultSectionSize(row_header.defaultSectionSize() + 10)
    self.active_table.setColumnWidth(0, 95)
    self.active_table.setColumnWidth(1, 80)
    self.active_table.setColumnWidth(2, 115)
    self.active_table.setColumnWidth(3, 100)

    _replace_next_actions_editor(self)
    _wire_dashboard_navigation(self)


def _refresh_active_with_status_pills(self, slots) -> None:
    assert _ORIGINAL_REFRESH_ACTIVE is not None
    _ORIGINAL_REFRESH_ACTIVE(self, slots)
    for row, slot in enumerate(slots):
        status = str(slot.status or "OPEN").upper()
        pill = _pill(status, status)
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(pill, 0, Qt.AlignmentFlag.AlignCenter)
        self.active_table.setCellWidget(row, 3, host)


def _refresh_coverage_with_colored_states(self, coverage) -> None:
    assert _ORIGINAL_REFRESH_COVERAGE is not None
    _ORIGINAL_REFRESH_COVERAGE(self, coverage)
    for index in range(self.coverage_grid.count()):
        item = self.coverage_grid.itemAt(index)
        widget = item.widget()
        if not isinstance(widget, QLabel):
            continue
        state = widget.property("dashboardCoverageState")
        if not state:
            continue
        background, border, foreground = _status_palette(str(state))
        widget.setStyleSheet(
            "QLabel {"
            f"color: {foreground}; background: {background}; border: 1px solid {border};"
            f"border-radius: {'0' if _is_rylo() else '9px'}; padding: 1px 7px; font-weight: 600;"
            "}"
        )


def _generated_next_actions(slots, coverage, optimization) -> str:
    open_slots = [slot.slot for slot in slots if slot.status == "OPEN"]
    needs_build = [slot.slot for slot in slots if slot.status == "NEEDS BUILD"]
    missing = [name for name, state in coverage.effects if state == "not_found" or state is False]
    unknown = sum(state == "unverified" for _, state in coverage.effects)
    actions: list[str] = []
    if "Off Tank" in open_slots:
        actions.append("☐  Assign an Off Tank.")
    dd_open = sum(1 for name in open_slots if name.startswith("DD "))
    if dd_open:
        actions.append(f"☐  Fill DD roster ({dd_open} slot(s) open).")
    if needs_build:
        actions.append(f"☐  Finish builds for {', '.join(needs_build[:3])}{'…' if len(needs_build) > 3 else ''}.")
    if missing:
        actions.append(f"☐  Review sources not identified: {', '.join(missing[:3])}{'…' if len(missing) > 3 else ''}.")
    if unknown:
        actions.append(f"☐  Review evidence for {unknown} unverified effect(s).")
    if optimization.capability_gaps:
        actions.append(f"☐  Review {optimization.capability_gaps} capability-resolution gap(s).")
    actions.append("☐  Load a saved team or send the current team to Roster.")
    actions.append("☐  Run a test parse and review Performance when the team is ready.")
    return "\n\n".join(actions[:6])


def _refresh_next_actions_editable(self, slots, coverage, optimization) -> None:
    editor = getattr(self, "next_actions_editor", None)
    if not isinstance(editor, QTextEdit):
        assert _ORIGINAL_REFRESH_NEXT_ACTIONS is not None
        _ORIGINAL_REFRESH_NEXT_ACTIONS(self, slots, coverage, optimization)
        return

    # Never overwrite unsaved user edits merely because the dashboard refreshes.
    if getattr(self, "_raid_engine_notes_dirty", False):
        return

    saved = _load_notes().get(_note_key(self), "")
    text = saved or _generated_next_actions(slots, coverage, optimization)
    editor.blockSignals(True)
    editor.setPlainText(text)
    editor.blockSignals(False)
    self._raid_engine_notes_dirty = False


def _builds_ui_with_centered_creator(self) -> None:
    assert _ORIGINAL_BUILDS_BUILD_UI is not None
    _ORIGINAL_BUILDS_BUILD_UI(self)
    _center_create_character_button(self)


def _overview_ui_with_centered_creator(self) -> None:
    assert _ORIGINAL_OVERVIEW_BUILD_UI is not None
    _ORIGINAL_OVERVIEW_BUILD_UI(self)
    _center_create_character_button(self)


def _overview_player_card_with_identity_gap(self, build):
    assert _ORIGINAL_OVERVIEW_PLAYER_CARD is not None
    card = _ORIGINAL_OVERVIEW_PLAYER_CARD(self, build)
    if build is None:
        return card
    identity = " • ".join(
        value for value in (build.EsoClass, build.Race, build.Role) if value
    )
    if not identity:
        return card
    for index in range(card.body_layout.count()):
        widget = card.body_layout.itemAt(index).widget()
        if isinstance(widget, QLabel) and widget.text() == identity:
            card.body_layout.insertSpacing(index + 1, 48)
            break
    return card


def _overview_raid_status_with_build_link(self):
    assert _ORIGINAL_OVERVIEW_RAID_STATUS_CARD is not None
    card = _ORIGINAL_OVERVIEW_RAID_STATUS_CARD(self)
    button = next(
        (candidate for candidate in card.body.findChildren(QPushButton) if candidate.text() == "Build"),
        None,
    )
    if button is not None:
        _rewire_button(button, lambda: _show_page(self, "console:2"))
    return card


def _overview_raid_schedule_with_centered_calendar(self, build):
    assert _ORIGINAL_OVERVIEW_RAID_SCHEDULE_CARD is not None
    card = _ORIGINAL_OVERVIEW_RAID_SCHEDULE_CARD(self, build)
    _center_named_card_button(card, "Open Calendar")
    return card


def _overview_skills_with_raid_review_link(self, build):
    assert _ORIGINAL_OVERVIEW_SKILLS_CARD is not None
    card = _ORIGINAL_OVERVIEW_SKILLS_CARD(self, build)
    button = _center_named_card_button(card, "Open Performance Focus")
    if button is not None:
        _rewire_button(button, lambda: _open_coverage_raid_review(self))
    return card


def _coverage_tab_without_scope_banner(self):
    assert _ORIGINAL_COVERAGE_TAB is not None
    page = _ORIGINAL_COVERAGE_TAB(self)
    scope_card = getattr(self, "scope_card", None)
    if scope_card is not None:
        scope_card.setVisible(False)
    return page


def _encounters_ui_without_overview_tab(self) -> None:
    assert _ORIGINAL_ENCOUNTERS_BUILD_UI is not None
    _ORIGINAL_ENCOUNTERS_BUILD_UI(self)
    tabs = getattr(self, "section_tabs", None)
    if tabs is None:
        return
    for index in range(tabs.count()):
        if tabs.tabText(index).strip().upper() == "OVERVIEW":
            tabs.setTabVisible(index, False)
            if tabs.currentIndex() == index and tabs.count() > 1:
                tabs.setCurrentIndex(1)
            break


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_REFRESH_ACTIVE
    global _ORIGINAL_REFRESH_COVERAGE, _ORIGINAL_REFRESH_NEXT_ACTIONS
    global _ORIGINAL_BUILDS_BUILD_UI, _ORIGINAL_OVERVIEW_BUILD_UI
    global _ORIGINAL_OVERVIEW_PLAYER_CARD, _ORIGINAL_OVERVIEW_RAID_STATUS_CARD
    global _ORIGINAL_OVERVIEW_RAID_SCHEDULE_CARD, _ORIGINAL_OVERVIEW_SKILLS_CARD
    global _ORIGINAL_COVERAGE_TAB, _ORIGINAL_ENCOUNTERS_BUILD_UI
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.coverage_page import CoveragePage
    from ui.encounters_page import EncountersPage
    from ui.operations_console import OperationsConsole
    from ui.raid_engine_dashboard_page import RaidEngineDashboardPage

    _ORIGINAL_INIT = RaidEngineDashboardPage.__init__
    _ORIGINAL_REFRESH_ACTIVE = RaidEngineDashboardPage._refresh_active_table
    _ORIGINAL_REFRESH_COVERAGE = RaidEngineDashboardPage._refresh_coverage
    _ORIGINAL_REFRESH_NEXT_ACTIONS = RaidEngineDashboardPage._refresh_next_actions
    _ORIGINAL_BUILDS_BUILD_UI = BuildsPage._build_ui
    _ORIGINAL_OVERVIEW_BUILD_UI = OperationsConsole._build_ui
    _ORIGINAL_OVERVIEW_PLAYER_CARD = OperationsConsole._player_card
    _ORIGINAL_OVERVIEW_RAID_STATUS_CARD = OperationsConsole._raid_status_card
    _ORIGINAL_OVERVIEW_RAID_SCHEDULE_CARD = OperationsConsole._raid_schedule_card
    _ORIGINAL_OVERVIEW_SKILLS_CARD = OperationsConsole._skills_to_work_on_card
    _ORIGINAL_COVERAGE_TAB = CoveragePage._coverage_tab
    _ORIGINAL_ENCOUNTERS_BUILD_UI = EncountersPage._build_ui

    RaidEngineDashboardPage.__init__ = _init_with_dashboard_polish
    RaidEngineDashboardPage._refresh_active_table = _refresh_active_with_status_pills
    RaidEngineDashboardPage._refresh_coverage = _refresh_coverage_with_colored_states
    RaidEngineDashboardPage._refresh_next_actions = _refresh_next_actions_editable
    BuildsPage._build_ui = _builds_ui_with_centered_creator
    OperationsConsole._build_ui = _overview_ui_with_centered_creator
    OperationsConsole._player_card = _overview_player_card_with_identity_gap
    OperationsConsole._raid_status_card = _overview_raid_status_with_build_link
    OperationsConsole._raid_schedule_card = _overview_raid_schedule_with_centered_calendar
    OperationsConsole._skills_to_work_on_card = _overview_skills_with_raid_review_link
    CoveragePage._coverage_tab = _coverage_tab_without_scope_banner
    EncountersPage._build_ui = _encounters_ui_without_overview_tab
    _INSTALLED = True
