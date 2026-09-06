from __future__ import annotations

from engine.config import get_data_dir
from minmax.optimization_mode import OptimizationMode
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.roster_service import RosterService
from services.team_role_autofill import build_role_compatible_autofill
from PySide6.QtWidgets import QComboBox, QLabel, QTableWidgetItem


_INSTALLED = False
_ORIGINAL_INIT = None


def _remove_combo_text(combo, text: str) -> None:
    index = combo.findText(text)
    if index >= 0:
        combo.removeItem(index)


def _hide_team_source(page) -> None:
    combo = getattr(page, "team_source_combo", None)
    if combo is None:
        return
    combo.setCurrentText("Saved Players Only")
    host = combo.parentWidget()
    if host is not None:
        host.hide()
    else:
        combo.hide()


def _hide_build_around(page) -> None:
    """Remove duplicate composition constraints from Optimization."""

    for name in ("required_slot_combo", "required_class_combo", "required_gear_input"):
        widget = getattr(page, name, None)
        if widget is not None:
            widget.hide()

    anchor = getattr(page, "required_slot_combo", None)
    host = anchor.parentWidget() if anchor is not None else None
    if host is not None:
        for label in host.findChildren(QLabel):
            if label.text().strip().upper() in {"BUILD AROUND", "CLASS", "REQUIRED SET(S)"}:
                label.hide()


def _team_names_for_member(member) -> set[str]:
    return {
        piece.strip().casefold()
        for piece in str(getattr(member, "Team", "") or "").split(",")
        if piece.strip()
    }


def _identity_values(value) -> set[str]:
    values = {
        str(getattr(value, field, "") or "").strip().casefold()
        for field in ("PlayerName", "CharacterName", "Name", "Gamertag")
    }
    return {item for item in values if item}


def _build_player_key(build, fallback: int) -> str:
    return (
        str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
        or str(getattr(build, "CharacterName", "") or "").strip()
        or f"build:{fallback}"
    )


def _active_team_table(page):
    if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
        return page.team_b_table
    return page.team_table


def _loaded_team_attr(page, table) -> str:
    return (
        "_optimization_loaded_team_name_b"
        if table is getattr(page, "team_b_table", None)
        else "_optimization_loaded_team_name_a"
    )


def _loaded_plan_attr(page, table) -> str:
    return (
        "_optimization_loaded_generated_plan_b"
        if table is getattr(page, "team_b_table", None)
        else "_optimization_loaded_generated_plan_a"
    )


def _remember_loaded_team(page, table, team_name: str, generated_plan=None) -> None:
    setattr(page, _loaded_team_attr(page, table), str(team_name or "").strip())
    setattr(page, _loaded_plan_attr(page, table), generated_plan)


def _loaded_team_name(page, table=None) -> str:
    target = table or _active_team_table(page)
    return str(getattr(page, _loaded_team_attr(page, target), "") or "").strip()


def _loaded_generated_plan(page, table=None):
    target = table or _active_team_table(page)
    return getattr(page, _loaded_plan_attr(page, target), None)


def _exact_saved_build_index(page, slot) -> int | None:
    wanted_people = {
        str(slot.player_name or "").strip().casefold(),
        str(slot.character_name or "").strip().casefold(),
    }
    wanted_people.discard("")
    wanted_build = str(slot.build_name or "").strip().casefold()
    for index, build in enumerate(page.roster.Members):
        if wanted_people and not (_identity_values(build) & wanted_people):
            continue
        build_name = str(getattr(build, "BuildName", "") or "").strip().casefold()
        if wanted_build and build_name != wanted_build:
            continue
        return index
    return None


def _row_by_slot_name(table) -> dict[str, int]:
    rows: dict[str, int] = {}
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        name = item.text().strip().casefold() if item is not None else ""
        if name:
            rows[name] = row
    return rows


def _load_generated_team_plan(page, plan) -> None:
    """Load an exact named generated plan without reranking its chairs."""

    table = _active_team_table(page)
    page._populate_team_editor(table, autofill=False)
    row_by_name = _row_by_slot_name(table)
    applied_saved = 0
    applied_recruits = 0

    page._team_combo_signal_guard = True
    try:
        for slot in plan.slots:
            row = row_by_name.get(str(slot.slot_name or "").strip().casefold())
            if row is None:
                continue
            selector = table.cellWidget(row, 1)
            if not isinstance(selector, QComboBox):
                continue

            build_index = _exact_saved_build_index(page, slot) if slot.kind == "saved" else None
            if build_index is not None:
                combo_index = selector.findData(build_index)
                if combo_index >= 0:
                    selector.setCurrentIndex(combo_index)
                    page._team_selection_changed(table, row)
                    applied_saved += 1
                    continue

            recruitment_value = f"recruitment:{row}"
            combo_index = selector.findData(recruitment_value)
            if combo_index >= 0:
                selector.setCurrentIndex(combo_index)
                page._team_selection_changed(table, row)
            table.setItem(row, 2, QTableWidgetItem(str(slot.eso_class or "Any class")))
            table.setItem(row, 3, QTableWidgetItem(str(slot.build_name or "Open requirement")))
            applied_recruits += 1
    finally:
        page._team_combo_signal_guard = False

    _remember_loaded_team(page, table, plan.name, plan)
    page._update_team_analysis()
    target = "Team B" if table is getattr(page, "team_b_table", None) else "Team A"
    page.status.success(
        f"Loaded team {plan.name!r} into {target}: {applied_saved} exact saved assignment(s), "
        f"{applied_recruits} recruit/open assignment(s)."
    )


def _load_roster_team(page, team_name: str) -> None:
    team = str(team_name or "").strip()
    if not team:
        return

    generated = page._optimization_generated_plan_service.load_plan(team)
    if generated is not None:
        _load_generated_team_plan(page, generated)
        return

    members = [
        member
        for member in page._optimization_roster_service.list_members()
        if team.casefold() in _team_names_for_member(member)
    ]
    member_keys: set[str] = set()
    for member in members:
        member_keys.update(_identity_values(member))

    eligible_indices = [
        index
        for index, build in enumerate(page.roster.Members)
        if _identity_values(build) & member_keys
    ]
    eligible_builds = [page.roster.Members[index] for index in eligible_indices]

    table = _active_team_table(page)
    page._populate_team_editor(table, autofill=False)
    assignments = build_role_compatible_autofill(
        slot_labels=tuple(page._role_slots()),
        build_roles=tuple(getattr(build, "Role", "") for build in eligible_builds),
        build_player_keys=tuple(
            _build_player_key(build, index)
            for index, build in enumerate(eligible_builds)
        ),
    )

    applied = 0
    page._team_combo_signal_guard = True
    try:
        for row, assignment in enumerate(assignments):
            if assignment.build_index is None:
                continue
            global_index = eligible_indices[assignment.build_index]
            selector = table.cellWidget(row, 1)
            if not isinstance(selector, QComboBox):
                continue
            combo_index = selector.findData(global_index)
            if combo_index < 0:
                continue
            selector.setCurrentIndex(combo_index)
            page._team_selection_changed(table, row)
            applied += 1
    finally:
        page._team_combo_signal_guard = False

    _remember_loaded_team(page, table, team, None)
    page._update_team_analysis()
    target = "Team B" if table is getattr(page, "team_b_table", None) else "Team A"
    page.status.success(
        f"Loaded roster team {team!r} into {target}: {applied} compatible saved player(s) "
        f"from {len(members)} roster member(s)."
    )


def _all_named_teams(page) -> tuple[str, ...]:
    names: dict[str, str] = {}
    for source in (
        page._optimization_roster_service.list_team_names(),
        page._optimization_generated_plan_service.list_plan_names(),
    ):
        for raw in source:
            name = str(raw or "").strip()
            if name:
                names.setdefault(name.casefold(), name)
    return tuple(sorted(names.values(), key=str.casefold))


def _install_load_team(page) -> None:
    db_path = get_data_dir() / "eso.db"
    page._optimization_roster_service = RosterService(EsoDatabase(db_path))
    page._optimization_generated_plan_service = GeneratedRosterPlanService(EsoDatabase(db_path))
    page._optimization_loaded_team_name_a = ""
    page._optimization_loaded_team_name_b = ""
    page._optimization_loaded_generated_plan_a = None
    page._optimization_loaded_generated_plan_b = None

    page.load_team_combo = QComboBox()
    page.load_team_combo.setMinimumWidth(190)
    page.load_team_combo.addItem("Select team…", "")
    for name in _all_named_teams(page):
        page.load_team_combo.addItem(name, name)
    page.load_team_combo.currentIndexChanged.connect(
        lambda *_: _load_roster_team(page, page.load_team_combo.currentData() or "")
    )
    page.header.add_context_widget(page._context_field("LOAD TEAM", page.load_team_combo))


def _refocus_optimization_ui(page) -> None:
    """Remove composition/prescription controls from the Optimization surface."""

    page.header.title.setText("Team Optimization")
    page.header.subtitle.setText(
        "Audit, improve, and compare an existing team. Composition creation lives in Comp Maker."
    )
    page.header.department.setText("RAID ENGINE • OPTIMIZATION")

    if hasattr(page, "generate_button"):
        page.generate_button.hide()
        page.generate_button.setEnabled(False)

    if hasattr(page, "change_card"):
        page.change_card.hide()
        page.change_card.setMaximumHeight(0)

    if hasattr(page, "team_source_combo"):
        _remove_combo_text(page.team_source_combo, "Recruitment Plan Only")
    _hide_team_source(page)
    _hide_build_around(page)
    _install_load_team(page)

    page.current_prescription = None
    page.status.info(
        f"Optimization ready • {len(page.roster.Members)} saved build(s) available. "
        "Load a named Roster team to audit, improve, or compare it."
    )


def _init_refocused(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)
    _refocus_optimization_ui(self)


def _original_slot_by_name(page) -> dict[str, GeneratedRosterPlanSlot]:
    plan = _loaded_generated_plan(page)
    if plan is None:
        return {}
    return {
        str(slot.slot_name or "").strip().casefold(): slot
        for slot in plan.slots
        if str(slot.slot_name or "").strip()
    }


def _slot_from_optimization_row(row: dict[str, str], original=None) -> GeneratedRosterPlanSlot:
    slot_name = row.get("slot", "")
    is_saved = row.get("kind") == "saved"
    player_name = row.get("player", "") or "Recruitment Needed"
    build_name = row.get("build", "") or "Open requirement"

    preserve_original = False
    if original is not None:
        if is_saved and original.kind == "saved":
            preserve_original = (
                str(original.player_name or "").strip().casefold()
                == str(player_name).strip().casefold()
                and str(original.build_name or "").strip().casefold()
                == str(build_name).strip().casefold()
            )
        elif not is_saved and original.kind != "saved":
            preserve_original = True

    if preserve_original:
        return GeneratedRosterPlanSlot(
            slot_name=slot_name or original.slot_name,
            kind=original.kind,
            player_name=original.player_name,
            character_name=original.character_name,
            eso_class=original.eso_class,
            build_name=original.build_name,
            gear_summary=original.gear_summary,
            unresolved=original.unresolved,
            role=original.role,
            source_kind=original.source_kind,
            source_name=original.source_name,
            source_url=original.source_url,
            candidate_id=original.candidate_id,
            gear_sets=original.gear_sets,
            skills=original.skills,
            mundus=original.mundus,
        )

    return GeneratedRosterPlanSlot(
        slot_name=slot_name,
        kind=("saved" if is_saved else "open_recruit"),
        player_name=player_name,
        character_name=row.get("character", ""),
        eso_class=row.get("class", "") or "Any class",
        build_name=build_name,
        role=slot_name,
        unresolved=(
            "Open recruitment requirement from Optimization."
            if not is_saved
            else ""
        ),
    )


def _send_visible_optimization_team_to_roster(window) -> None:
    """Persist the visible Optimization team back under its loaded team identity."""

    optimization_page = window.pages.get("console:6")
    plan_rows = window._current_optimized_team_plan()
    if not plan_rows:
        if optimization_page is not None:
            optimization_page.status.warning(
                "No team slots are selected. Load a Roster team before sending it back to Roster."
            )
        return

    originals = _original_slot_by_name(optimization_page)
    slots = tuple(
        _slot_from_optimization_row(
            row,
            originals.get(str(row.get("slot", "")).strip().casefold()),
        )
        for row in plan_rows
    )

    goal = optimization_page.goal_combo.currentText().strip() or "Custom Goal"
    team_name = _loaded_team_name(optimization_page) or f"{goal} Optimized Team"
    roster_page = window.pages["roster_page"]
    plan = roster_page.generated_plan_service.save_plan(
        name=team_name,
        goal=goal,
        difficulty=optimization_page.difficulty_combo.currentText(),
        slots=slots,
    )
    _remember_loaded_team(
        optimization_page,
        _active_team_table(optimization_page),
        plan.name,
        plan,
    )
    roster_page._refresh_generated_plan_choices(plan.name)
    roster_page.view_combo.setCurrentText("Generated Team")
    roster_page.tabs.setCurrentIndex(0)
    roster_page._populate_assignment_table()

    saved = sum(1 for slot in slots if slot.kind == "saved")
    recruits = len(slots) - saved
    optimization_page.status.success(
        f"Updated team {plan.name!r} in Roster: {saved} saved player(s), "
        f"{recruits} open recruit slot(s)."
    )
    window.show_page("roster_page")


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage
    from ui.main_window import MainWindow

    OptimizationPage._MODE_ORDER = (
        OptimizationMode.AUDIT,
        OptimizationMode.BUILD,
        OptimizationMode.COMPARE,
    )

    _ORIGINAL_INIT = OptimizationPage.__init__
    OptimizationPage.__init__ = _init_refocused
    MainWindow._send_optimized_team_to_roster = _send_visible_optimization_team_to_roster
    _INSTALLED = True
