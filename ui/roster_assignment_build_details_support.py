from __future__ import annotations

import re

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextEdit, QVBoxLayout


_INSTALLED = False
_ORIGINAL_ROSTER_INIT = None


_SKILLS_RE = re.compile(r"Observed/known skills:\s*(.*?)(?:\.\s|$)", re.IGNORECASE)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _public_build_name(player_name: str, build_name: str) -> str:
    """Hide the source log player's identity from recruit-facing labels."""

    player = _clean(player_name)
    build = _clean(build_name)
    if player.casefold() != "recruitment needed" or " • " not in build:
        return build
    parts = [part.strip() for part in build.split(" • ") if part.strip()]
    return " • ".join(parts[:-1]) if len(parts) >= 3 else build


def _selected_generated_plan(page):
    service = getattr(page, "generated_plan_service", None)
    if service is None:
        return None
    combo = getattr(page, "generated_plan_combo", None)
    name = combo.currentText().strip() if combo is not None else ""
    return service.load_plan(name) if name else service.latest_plan()


def _slot_for_row(page, row: int):
    plan = _selected_generated_plan(page)
    if plan is None or row < 0:
        return None
    slot_item = page.assignment_table.item(row, 1)
    slot_name = _clean(slot_item.text() if slot_item is not None else "")
    for slot in plan.slots:
        if _clean(slot.slot_name).casefold() == slot_name.casefold():
            return slot
    return None


def _saved_build_for_slot(page, slot):
    player = _clean(slot.player_name).casefold()
    build_name = _clean(slot.build_name).casefold()
    if not player or player == "recruitment needed":
        return None
    roster = getattr(page, "roster", None)
    for build in getattr(roster, "Members", ()):
        owner = (
            _clean(getattr(build, "Name", ""))
            or _clean(getattr(build, "Gamertag", ""))
        ).casefold()
        saved_name = _clean(getattr(build, "BuildName", "")).casefold()
        if owner == player and (not build_name or saved_name == build_name):
            return build
    return None


def _skills_from_slot(slot) -> tuple[str, ...]:
    match = _SKILLS_RE.search(_clean(slot.unresolved))
    if match is None:
        return ()
    values = []
    seen = set()
    for piece in match.group(1).split(","):
        value = _clean(piece)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            values.append(value)
    return tuple(values)


def _saved_skills(build) -> tuple[str, ...]:
    values = []
    seen = set()
    for raw in (
        *getattr(build, "FrontBarSkills", ()),
        *getattr(build, "BackBarSkills", ()),
    ):
        value = _clean(raw)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            values.append(value)
    return tuple(values)


def _details_text(page, slot) -> str:
    player = _clean(slot.player_name) or "Recruitment Needed"
    build_name = _public_build_name(player, slot.build_name) or "Open requirement"
    saved_build = _saved_build_for_slot(page, slot)

    gear = tuple(
        value.strip()
        for value in _clean(slot.gear_summary).split("+")
        if value.strip()
    )
    skills = _saved_skills(saved_build) if saved_build is not None else _skills_from_slot(slot)

    lines = [
        player,
        f"Class: {_clean(slot.eso_class) or 'Any class'}",
        f"Role: {_clean(slot.slot_name) or 'Unresolved'}",
        f"Build: {build_name}",
        "",
        "GEAR",
    ]
    lines.extend(f"• {value}" for value in gear) if gear else lines.append("• No gear detail recorded")
    lines.extend(("", "SKILLS / ABILITIES"))
    lines.extend(f"• {value}" for value in skills) if skills else lines.append("• No skill detail recorded")

    if saved_build is None and _clean(slot.unresolved):
        lines.extend(
            (
                "",
                "SOURCE BOUNDARY",
                "This recruit setup is sourced evidence. Missing traits, enchants, CP, bar placement, food, potions, or other fields remain unresolved rather than being invented.",
            )
        )
    return "\n".join(lines)


def _show_assignment_details(page, row: int) -> None:
    if getattr(page, "view_combo", None) is None:
        return
    if page.view_combo.currentText().strip() != "Generated Team":
        return

    slot = _slot_for_row(page, row)
    if slot is None:
        page.status.info("No generated build details are available for this assignment.")
        return

    player = _clean(slot.player_name) or "Recruitment Needed"
    build_name = _public_build_name(player, slot.build_name) or "Open requirement"
    dialog = QDialog(page)
    dialog.setWindowTitle(f"Assignment Build • {player} • {build_name}")
    dialog.resize(620, 520)
    layout = QVBoxLayout(dialog)
    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(_details_text(page, slot))
    layout.addWidget(text, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.clicked.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()


def _assignment_item_clicked(page, item) -> None:
    # Player and Build are the two human-facing assignment names in the table.
    if item is None or item.column() not in {0, 3}:
        return
    _show_assignment_details(page, item.row())


def _roster_init_with_assignment_details(self, parent=None) -> None:
    assert _ORIGINAL_ROSTER_INIT is not None
    _ORIGINAL_ROSTER_INIT(self, parent)
    self.assignment_table.itemClicked.connect(
        lambda item: _assignment_item_clicked(self, item)
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_ROSTER_INIT
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    _ORIGINAL_ROSTER_INIT = RosterPage.__init__
    RosterPage.__init__ = _roster_init_with_assignment_details
    _INSTALLED = True
