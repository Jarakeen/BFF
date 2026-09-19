from __future__ import annotations

"""Carry roster-owned player/class/role/job context into Comp Builder without inventing builds."""

from types import SimpleNamespace

from PySide6.QtWidgets import QComboBox, QHeaderView, QInputDialog, QTableWidgetItem

from services.roster_assignment_context_service import RosterAssignmentContextService
from services.team_composition_catalog import flexible_raid_slots
from ui.roster_encounter_assignment_context_support import (
    selected_encounter_id,
    selected_encounter_name,
)


_INSTALLED = False
PLAYER_COLUMN = 11


def _role_key(value: object) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    if "tank" in text:
        return "tank"
    if "heal" in text:
        return "healer"
    if "damage" in text or "dps" in text:
        return "damage"
    words = text.replace("/", " ").replace("-", " ").split()
    if "dd" in words:
        return "damage"
    return ""


def _row_role(page, row: int) -> str:
    return _role_key(page._cell_text(row, 1))


def _player_label(member) -> str:
    player = str(getattr(member, "PlayerName", "") or "").strip()
    character = str(getattr(member, "CharacterName", "") or "").strip()
    if player and character:
        return f"{player} • {character}"
    return player or character or "Unnamed"


def _is_recruit_member(member) -> bool:
    values = (
        getattr(member, "PlayerName", ""),
        getattr(member, "CharacterName", ""),
    )
    normalized = {
        " ".join(str(value or "").strip().casefold().split())
        for value in values
        if str(value or "").strip()
    }
    return any(
        value == "recruit"
        or value == "recruitment needed"
        or value.startswith("recruit ")
        for value in normalized
    )


def _group_size_for_members(members) -> int:
    """Roster intake supports the two ESO group sizes Comp Builder is meant to plan."""
    return 4 if len(tuple(members)) <= 4 else 12


def _canonical_seat_id(value: object) -> str:
    return "-".join(
        str(value or "")
        .strip()
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _ensure_unbound_comp_state(
    page,
    *,
    team_name: str,
    encounter_name: str,
) -> None:
    """Create canonical Comp state when roster/assignments arrive before Raid Plan."""
    existing = getattr(page, "_comp_plan_state", None)
    if existing is not None and existing.is_raid_plan_bound:
        return

    from models.comp_plan_state import CompChairState
    from services.comp_plan_state_service import CompPlanStateService
    from ui.comp_builder_page import GOAL_TRIALS

    goal = str(page.goal_combo.currentText() or "").strip() or "Custom Goal"
    trial = str(
        GOAL_TRIALS.get(goal)
        or encounter_name
        or "Custom Trial"
    ).strip()
    suffix = f" • {encounter_name}" if encounter_name else ""
    name = f"{team_name or 'Ad-hoc Team'}{suffix}".strip()

    chairs = tuple(
        CompChairState(
            seat_id=_canonical_seat_id(
                page._cell_text(row, 0) or f"slot-{row + 1}"
            ),
            role=str(page._cell_text(row, 1) or "").strip() or None,
        )
        for row in range(page.matrix_table.rowCount())
    )
    if existing is not None:
        page._comp_unbound_baseline_state = existing.mark_saved()
    page._comp_plan_state = CompPlanStateService.new_unbound(
        raid_plan_name=name or f"{goal} Composition",
        trial_id=trial,
        team_name=str(team_name or "").strip() or None,
        difficulty=str(page.difficulty_combo.currentText() or "").strip() or None,
        achievement_goal=goal,
        chairs=chairs,
    )


def _load_roster_shape(page, group_size: int) -> None:
    """Load a neutral 4- or 12-player skeleton without asserting a trial template."""
    page.current_template = None
    page.current_slots = flexible_raid_slots(group_size)
    page._render_slots(page.current_slots)

    if group_size == 4:
        page.matrix_table.setMinimumHeight(190)
        page.matrix_table.setMaximumHeight(190)
        page.matrix_card.setMinimumHeight(235)
        page.matrix_card.setMaximumHeight(255)
    else:
        page.matrix_table.setMinimumHeight(430)
        page.matrix_table.setMaximumHeight(430)
        page.matrix_card.setMinimumHeight(470)
        page.matrix_card.setMaximumHeight(480)

    goal = page.goal_combo.currentText().strip() or "Custom Goal"
    page.plan_name_input.setText(f"{goal} Composition")
    if hasattr(page, "trial_label"):
        page.trial_label.setText(
            f"GROUP SIZE\n{group_size}\n\nGOAL\n{goal}"
        )
    if hasattr(page, "summary_label"):
        shape = "1 Tank • 1 Healer • 2 Damage Dealers" if group_size == 4 else (
            "2 Tanks • 2 Healers • 8 Damage Dealers"
        )
        page.summary_label.setText(
            f"Roster-driven composition\n{shape}\n\n"
            "Players are fixed by the loaded roster. Builds remain recommendations until assigned."
        )
    if hasattr(page, "evidence_text"):
        page.evidence_text.setPlainText(
            "Roster intake preserves player identity and opens only build/provider decisions. "
            "Recruit placeholders remain open prescription slots rather than invented players."
        )
    if hasattr(page, "_refresh_coverage"):
        page._refresh_coverage()


def _ensure_player_column(page) -> None:
    table = page.matrix_table
    if table.columnCount() <= PLAYER_COLUMN:
        table.setColumnCount(PLAYER_COLUMN + 1)
    header_item = table.horizontalHeaderItem(PLAYER_COLUMN)
    if header_item is None:
        header_item = QTableWidgetItem("PLAYER")
        table.setHorizontalHeaderItem(PLAYER_COLUMN, header_item)
    else:
        header_item.setText("PLAYER")
    header = table.horizontalHeader()
    header.setSectionResizeMode(PLAYER_COLUMN, QHeaderView.ResizeMode.Stretch)
    visual_index = header.visualIndex(PLAYER_COLUMN)
    if visual_index > 0:
        header.moveSection(visual_index, 0)


def _set_class_constraint(page, row: int, eso_class: str) -> None:
    text = str(eso_class or "").strip()
    if not text:
        return
    class_combo = page.matrix_table.cellWidget(row, 2)
    if not isinstance(class_combo, QComboBox):
        return
    match = next(
        (
            index
            for index in range(class_combo.count())
            if str(class_combo.itemText(index) or "").strip().casefold() == text.casefold()
        ),
        -1,
    )
    if match >= 0 and class_combo.currentIndex() != match:
        class_combo.blockSignals(True)
        try:
            class_combo.setCurrentIndex(match)
        finally:
            class_combo.blockSignals(False)


def _reapply_class_constraints(page) -> None:
    constraints = dict(getattr(page, "_comp_class_constraint_by_slot", {}) or {})
    if not constraints:
        return
    for row in range(page.matrix_table.rowCount()):
        slot_name = str(page._cell_text(row, 0) or "").strip()
        if not slot_name:
            continue
        eso_class = constraints.get(slot_name)
        if eso_class:
            _set_class_constraint(page, row, eso_class)


def apply_raid_plan_class_constraints(page, class_by_seat: dict[str, str]) -> None:
    """Apply explicit Raid Plan seat classes as authoritative chair constraints."""
    cleaned = {
        str(seat or "").strip(): str(eso_class or "").strip()
        for seat, eso_class in dict(class_by_seat or {}).items()
        if str(seat or "").strip() and str(eso_class or "").strip()
    }
    page._raid_plan_class_by_seat = cleaned
    page._comp_class_constraint_by_slot = dict(cleaned)
    _reapply_class_constraints(page)


def _set_player(page, row: int, member, assignment: dict | None = None) -> None:
    _ensure_player_column(page)
    item = page.matrix_table.item(row, PLAYER_COLUMN)
    if item is None:
        item = QTableWidgetItem()
        page.matrix_table.setItem(row, PLAYER_COLUMN, item)
    item.setText(_player_label(member))
    job = str((assignment or {}).get("primary_assignment", "") or "").strip()
    tooltip = "Roster player carried into Comp Builder. This does not imply a saved build exists."
    if job:
        tooltip += f"\nRaid job for this context: {job}."
    item.setToolTip(tooltip)

    eso_class = str(getattr(member, "EsoClass", "") or "").strip()
    if eso_class:
        _set_class_constraint(page, row, eso_class)


def _clear_player_rows(page) -> None:
    _ensure_player_column(page)
    for row in range(page.matrix_table.rowCount()):
        item = page.matrix_table.item(row, PLAYER_COLUMN)
        if item is None:
            item = QTableWidgetItem()
            page.matrix_table.setItem(row, PLAYER_COLUMN, item)
        item.setText("")
        item.setToolTip("")


def _match_rows(page, members) -> list[tuple[int, object]]:
    """Place roster members into matching Comp Builder role chairs.

    Known-role players are placed first so an unresolved roster role cannot steal
    a Tank/Healer chair before a real Tank/Healer is processed. Within each role,
    roster order is preserved.
    """
    available = list(range(page.matrix_table.rowCount()))
    matches: list[tuple[int, object]] = []
    members = list(members)

    # Raid Plan handoffs carry the exact canonical chair. Honor that before role
    # matching so Main Tank/Off Tank and numbered DD chairs survive a round trip.
    remaining: list[object] = []
    for member in members:
        wanted_seat = str(getattr(member, "RaidSeatId", "") or "").strip().casefold()
        if not wanted_seat:
            remaining.append(member)
            continue
        row = next(
            (
                candidate_row
                for candidate_row in available
                if str(page._cell_text(candidate_row, 0) or "").strip().casefold()
                == wanted_seat
            ),
            None,
        )
        if row is None:
            remaining.append(member)
            continue
        available.remove(row)
        matches.append((row, member))

    members = remaining
    known = [member for member in members if _role_key(getattr(member, "PrimaryRole", ""))]
    unknown = [member for member in members if not _role_key(getattr(member, "PrimaryRole", ""))]

    for member in known:
        wanted = _role_key(getattr(member, "PrimaryRole", ""))
        row = next((r for r in available if _row_role(page, r) == wanted), None)
        if row is None:
            row = available[0] if available else None
        if row is None:
            break
        available.remove(row)
        matches.append((row, member))

    for member in unknown:
        if not available:
            break
        row = available.pop(0)
        matches.append((row, member))

    return matches


def _sync_comp_state_from_matches(page, matched, assignments: dict[int, dict] | None = None) -> None:
    state = getattr(page, "_comp_plan_state", None)
    if state is None:
        return

    current = state
    assignments = dict(assignments or {})
    for row, member in matched:
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        wanted = "-".join(
            str(slot_name or "")
            .strip()
            .casefold()
            .replace("_", " ")
            .replace("-", " ")
            .split()
        )
        chair = next(
            (
                item
                for item in current.chairs
                if "-".join(
                    str(item.seat_id or "")
                    .strip()
                    .casefold()
                    .replace("_", " ")
                    .replace("-", " ")
                    .split()
                )
                == wanted
            ),
            None,
        )
        if chair is None:
            continue

        changes: dict[str, object] = {}
        player = str(getattr(member, "PlayerName", "") or "").strip()
        recruit = _is_recruit_member(member)
        if not chair.is_locked("player"):
            changes["player_name"] = "" if recruit else player

        character = str(getattr(member, "CharacterName", "") or "").strip()
        if character and not chair.is_locked("character"):
            changes["character_name"] = character

        role = str(getattr(member, "PrimaryRole", "") or "").strip()
        if role and not chair.is_locked("role"):
            changes["role"] = role

        eso_class = str(getattr(member, "EsoClass", "") or "").strip()
        if eso_class and not chair.is_locked("class"):
            changes["eso_class"] = eso_class

        member_id = int(member.Id) if getattr(member, "Id", None) is not None else -1
        assignment = assignments.get(member_id, {})
        primary = str(assignment.get("primary_assignment", "") or "").strip()
        secondary = str(assignment.get("secondary_assignment", "") or "").strip()
        note = str(assignment.get("notes", "") or "").strip()
        if primary and not chair.is_locked("primary_assignment"):
            changes["primary_assignment"] = primary
        if secondary and not chair.is_locked("secondary_assignment"):
            changes["secondary_assignment"] = secondary
        if note and not chair.notes:
            changes["notes"] = note

        if changes:
            current = current.with_chair(chair.with_changes(**changes))

    page._comp_plan_state = current


def apply_roster_team_context(
    page,
    team_name: str,
    members,
    *,
    encounter_id: str = "",
    encounter_name: str = "",
    assignments: dict[int, dict] | None = None,
    group_size: int | None = None,
) -> None:
    members = tuple(members)
    assignments = dict(assignments or {})
    page._roster_team_context_name = str(team_name or "").strip()
    page._roster_encounter_context_id = str(encounter_id or "").strip()
    page._roster_encounter_context_name = str(encounter_name or "").strip()
    page._roster_team_context_member_ids = tuple(
        int(member.Id) for member in members if getattr(member, "Id", None) is not None
    )
    page._roster_team_context_members = members
    page._roster_team_context_assignments = assignments

    # Roster size owns the neutral group shape. Four-person groups stay four-person;
    # trial rosters stay twelve-person. Team/boss assignment remains context and must
    # never invent extra people or silently expand a dungeon group into a trial.
    group_size = 4 if group_size == 4 else 12 if group_size == 12 else _group_size_for_members(members)
    page._comp_group_size = group_size
    _load_roster_shape(page, group_size)
    _clear_player_rows(page)
    _ensure_unbound_comp_state(
        page,
        team_name=page._roster_team_context_name,
        encounter_name=page._roster_encounter_context_name,
    )

    matched = _match_rows(page, members)
    page._comp_roster_member_by_slot = {}
    page._comp_class_constraint_by_slot = {}
    for row, member in matched:
        member_id = int(member.Id) if getattr(member, "Id", None) is not None else -1
        _set_player(page, row, member, assignments.get(member_id))
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        eso_class = str(getattr(member, "EsoClass", "") or "").strip()
        if eso_class:
            page._comp_class_constraint_by_slot[slot_name] = eso_class
        page._comp_roster_member_by_slot[slot_name] = None if _is_recruit_member(member) else member

    _sync_comp_state_from_matches(page, matched, assignments)
    _reapply_class_constraints(page)

    if hasattr(page, "plan_name_input") and page._roster_team_context_name:
        suffix = f" • {page._roster_encounter_context_name}" if page._roster_encounter_context_name else ""
        page.plan_name_input.setText(f"{page._roster_team_context_name}{suffix}")

    state = getattr(page, "_comp_plan_state", None)
    if state is not None and not state.is_raid_plan_bound:
        from dataclasses import replace

        page._comp_plan_state = replace(
            state,
            raid_plan_name=str(page.plan_name_input.text() or state.raid_plan_name).strip(),
            team_name=page._roster_team_context_name or state.team_name,
            dirty=True,
        )

    if hasattr(page, "_refresh_coverage"):
        page._refresh_coverage()

    role_counts = {"tank": 0, "healer": 0, "damage": 0, "unresolved": 0}
    for member in members:
        key = _role_key(getattr(member, "PrimaryRole", "")) or "unresolved"
        role_counts[key] += 1
    context_label = page._roster_team_context_name or "selected team"
    if page._roster_encounter_context_name:
        context_label = f"{context_label} • {page._roster_encounter_context_name}"
    page.status.info(
        f"Loaded {len(matched)} roster slot(s) from {context_label} into a {group_size}-player Comp Builder plan: "
        f"{role_counts['tank']} tank, {role_counts['healer']} healer, "
        f"{role_counts['damage']} DD, {role_counts['unresolved']} unresolved. "
        "Classes and raid jobs are carried over; empty builds remain intentionally unresolved."
    )


def _send_roster_team_to_comp(page) -> None:
    from ui import roster_assignment_action_support as assignment_actions

    team_name = assignment_actions._selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team in Assignments before sending it to Comp Builder.")
        return
    members = assignment_actions._team_members(page, team_name)
    if not members:
        page.status.warning(f"{team_name} has no roster members to send to Comp Builder.")
        return

    encounter_id = selected_encounter_id(page)
    encounter_name = selected_encounter_name(page)
    context_service = getattr(page, "assignment_context_service", None)
    if context_service is None:
        context_service = RosterAssignmentContextService(page.database)

    assignments: dict[int, dict] = {}
    for member in members:
        if getattr(member, "Id", None) is None:
            continue
        assignments[int(member.Id)] = context_service.get_effective_assignment(
            int(member.Id),
            team_name=team_name,
            encounter_id=encounter_id,
            legacy_service=page.roster_service,
        )

    if not assignment_actions._show_page(page, "comp_builder"):
        return

    comp = getattr(page.window(), "pages", {}).get("comp_builder")
    if comp is None or not hasattr(comp, "apply_roster_team_context"):
        page.status.warning("Comp Builder opened, but the roster intake bridge is unavailable.")
        return
    comp.apply_roster_team_context(
        team_name,
        members,
        encounter_id=encounter_id,
        encounter_name=encounter_name,
        assignments=assignments,
    )




def _team_list_names(text: str) -> tuple[str, ...]:
    normalized = str(text or "").replace(",", "\n")
    return tuple(
        line.strip()
        for line in normalized.splitlines()
        if line.strip()
    )[:12]


def open_team_list_dialog(page) -> None:
    text, accepted = QInputDialog.getMultiLineText(
        page,
        "Load Team List",
        "One player per line. Use Recruit for any open spot.",
        "",
    )
    if not accepted:
        return
    names = _team_list_names(text)
    if not names:
        page.status.warning("No player names were entered.")
        return

    members = tuple(
        SimpleNamespace(
            Id=None,
            PlayerName=name,
            CharacterName="",
            PrimaryRole="",
            EsoClass="",
        )
        for name in names
    )
    group_size = 4 if len(names) <= 4 else 12
    apply_roster_team_context(
        page,
        "Ad-hoc Team",
        members,
        group_size=group_size,
    )

def _flatten_attention_card(page) -> None:
    card = getattr(page, "attention_card", None)
    if card is None:
        return
    card.header.hide()
    card.setProperty("flatActionCard", True)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui.themed_roster_page import RosterPage
    from ui import roster_assignment_action_support as assignment_actions

    original_init = CompBuilderPage.__init__
    original_render_slots = CompBuilderPage._render_slots

    def init_with_roster_intake(self, parent=None):
        original_init(self, parent)
        _ensure_player_column(self)
        self._comp_class_constraint_by_slot = {}

    def render_slots_with_class_constraints(self, slots) -> None:
        original_render_slots(self, slots)
        _reapply_class_constraints(self)

    CompBuilderPage.__init__ = init_with_roster_intake
    CompBuilderPage._render_slots = render_slots_with_class_constraints
    CompBuilderPage.apply_roster_team_context = apply_roster_team_context

    assignment_actions._send_to_comp_maker = _send_roster_team_to_comp

    original_refresh_summary_cards = RosterPage._refresh_summary_cards

    def refresh_summary_cards_flat(self):
        result = original_refresh_summary_cards(self)
        _flatten_attention_card(self)
        return result

    RosterPage._refresh_summary_cards = refresh_summary_cards_flat
    _INSTALLED = True
