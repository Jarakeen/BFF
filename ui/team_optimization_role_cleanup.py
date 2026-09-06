from __future__ import annotations

from engine.config import get_data_dir
from minmax.optimization_mode import OptimizationMode
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import GeneratedRosterPlanSlot
from services.roster_service import RosterService
from services.team_role_autofill import build_role_compatible_autofill
from PySide6.QtWidgets import QComboBox, QLabel


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
    # Keep the legacy source-mode control alive because the prescription pipeline
    # still reads it internally. Optimization users now load a real named Roster
    # team instead of choosing an implementation-level candidate source.
    combo.setCurrentText("Saved Players Only")
    host = combo.parentWidget()
    if host is not None:
        host.hide()
    else:
        combo.hide()


def _hide_build_around(page) -> None:
    """Remove duplicate composition constraints from Optimization.

    Comp Maker owns chair/class/required-set composition design. The underlying
    PrescribedSlotBuildConstraint machinery remains intact for callers/tests; only
    the redundant Optimization-page editor is removed.
    """

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


def _load_roster_team(page, team_name: str) -> None:
    team = str(team_name or "").strip()
    if not team:
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
    # Rebuild the editor without generic autofill, then assign only saved builds
    # belonging to the selected named Roster team.
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

    page._update_team_analysis()
    target = "Team B" if table is getattr(page, "team_b_table", None) else "Team A"
    page.status.success(
        f"Loaded roster team {team!r} into {target}: {applied} compatible saved player(s) "
        f"from {len(members)} roster member(s)."
    )


def _install_load_team(page) -> None:
    page._optimization_roster_service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))
    page.load_team_combo = QComboBox()
    page.load_team_combo.setMinimumWidth(190)
    page.load_team_combo.addItem("Select roster team…", "")
    for name in page._optimization_roster_service.list_team_names():
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


def _send_visible_optimization_team_to_roster(window) -> None:
    """Persist the visible Optimization team as a generated roster plan."""

    optimization_page = window.pages.get("console:6")
    plan_rows = window._current_optimized_team_plan()
    if not plan_rows:
        if optimization_page is not None:
            optimization_page.status.warning(
                "No team slots are selected. Load a Roster team before sending it back to Roster."
            )
        return

    slots = tuple(
        GeneratedRosterPlanSlot(
            slot_name=row.get("slot", ""),
            kind=("saved" if row.get("kind") == "saved" else "open_recruit"),
            player_name=row.get("player", "") or "Recruitment Needed",
            character_name=row.get("character", ""),
            eso_class=row.get("class", "") or "Any class",
            build_name=row.get("build", "") or "Open requirement",
            gear_summary="",
            unresolved=(
                "Open recruitment requirement from Optimization."
                if row.get("kind") != "saved"
                else ""
            ),
        )
        for row in plan_rows
    )

    goal = optimization_page.goal_combo.currentText().strip() or "Custom Goal"
    roster_page = window.pages["roster_page"]
    plan = roster_page.generated_plan_service.save_plan(
        name=f"{goal} Optimized Team",
        goal=goal,
        difficulty=optimization_page.difficulty_combo.currentText(),
        slots=slots,
    )
    roster_page._refresh_generated_plan_choices(plan.name)
    roster_page.view_combo.setCurrentText("Generated Team")
    roster_page.tabs.setCurrentIndex(0)
    roster_page._populate_assignment_table()

    saved = sum(1 for slot in slots if slot.kind == "saved")
    recruits = len(slots) - saved
    optimization_page.status.success(
        f"Sent {plan.name} to Roster: {saved} saved player(s), "
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
