from __future__ import annotations

"""Add one simple encounter selector to Assignments.

The user first chooses a team, then optionally chooses a boss. Team Default is the
normal assignment. Choosing a boss means edits become that boss's override. No
extra workflow or duplicate assignment screen is introduced.
"""

from PySide6.QtWidgets import QComboBox, QLabel, QWidget, QHBoxLayout

from engine.config import get_data_dir
from services.encounter_repository import EncounterRepository
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_TEAM_DEFAULT_LABEL = "Team Default"


def _encounter_choices() -> tuple[tuple[str, str], ...]:
    try:
        repository = EncounterRepository.from_data_root(get_data_dir())
    except Exception:
        return ()

    choices: list[tuple[str, str]] = []
    for encounter_id in repository.encounter_ids():
        try:
            definition = repository.get(encounter_id)
        except Exception:
            continue
        name = str(definition.name or encounter_id).strip()
        if name:
            choices.append((name, encounter_id))
    return tuple(sorted(choices, key=lambda item: item[0].casefold()))


def selected_encounter_id(page) -> str:
    combo = getattr(page, "assignment_encounter_combo", None)
    if combo is None:
        return ""
    return str(combo.currentData() or "").strip()


def selected_encounter_name(page) -> str:
    combo = getattr(page, "assignment_encounter_combo", None)
    if combo is None or not selected_encounter_id(page):
        return ""
    return str(combo.currentText() or "").strip()


def _set_enabled_state(page) -> None:
    combo = getattr(page, "assignment_encounter_combo", None)
    if combo is None:
        return
    team_name = str(getattr(page, "assignment_team_filter", "") or "").strip()
    combo.setEnabled(bool(team_name))
    combo.setToolTip(
        "Choose a boss only when this team member has a different job for that fight."
        if team_name
        else "Choose a team first."
    )


def _encounter_changed(page, _index: int) -> None:
    if hasattr(page, "_populate_assignment_table"):
        page._populate_assignment_table()
    encounter = selected_encounter_name(page)
    if encounter:
        page.status.info(
            f"Assignments showing {encounter}. Changes here become boss-specific overrides."
        )
    else:
        team_name = str(getattr(page, "assignment_team_filter", "") or "").strip()
        if team_name:
            page.status.info(
                f"Assignments showing {team_name} team defaults. Bosses inherit these unless overridden."
            )


def _find_assignments_card(page_widget) -> FoundryCard | None:
    for card in page_widget.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Player Assignments":
            return card
    return None


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_assignments_tab = RosterPage._build_assignments_tab
    original_populate_assignment_table = RosterPage._populate_assignment_table

    def build_assignments_tab_with_encounter_context(self):
        page = original_build_assignments_tab(self)
        card = _find_assignments_card(page)
        if card is None:
            return page

        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        label = QLabel("Boss")
        label.setProperty("muted", True)
        combo = QComboBox()
        combo.setMinimumWidth(220)
        combo.addItem(_TEAM_DEFAULT_LABEL, "")
        for name, encounter_id in _encounter_choices():
            combo.addItem(name, encounter_id)
        combo.currentIndexChanged.connect(lambda index: _encounter_changed(self, index))
        row.addWidget(label)
        row.addWidget(combo)
        card.header_action_layout.addWidget(wrapper)
        self.assignment_encounter_combo = combo
        _set_enabled_state(self)
        return page

    def populate_assignment_table_with_encounter_context(self, *args, **kwargs):
        _set_enabled_state(self)
        return original_populate_assignment_table(self, *args, **kwargs)

    RosterPage._build_assignments_tab = build_assignments_tab_with_encounter_context
    RosterPage._populate_assignment_table = populate_assignment_table_with_encounter_context
    _INSTALLED = True


__all__ = ["install", "selected_encounter_id", "selected_encounter_name"]
