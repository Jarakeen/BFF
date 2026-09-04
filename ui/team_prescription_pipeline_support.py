from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from engine.config import get_data_dir
from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds
from services.team_prescription_pipeline import run_automatic_team_prescription_candidate_pipeline
from services.team_prescription_preview import format_prescribed_roster_preview
from services.team_prescription_saved_build_evaluator import (
    SavedBuildPrescriptionEvaluationSettings,
    SavedBuildPrescriptionObjectiveEvaluator,
    build_saved_player_prescription_candidates,
)
from services.team_role_autofill import normalize_team_role
from services.team_prescription_slot_constraints import project_slot_build_constraints


_INSTALLED = False
_ORIGINAL_POPULATE_TEAM_EDITOR = None


def _player_key(build, index: int) -> str:
    identity = (
        str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
    )
    return identity.casefold() if identity else f"unnamed-build:{index}"


def _tank_anchor_builds(page):
    return tuple(
        build
        for build in page.roster.Members
        if normalize_team_role(getattr(build, "Role", "")) == "tank"
    )


def _selected_saved_builds(page) -> tuple:
    selected: list = []
    used_players: set[str] = set()
    for row in range(page.team_table.rowCount()):
        selector = page.team_table.cellWidget(row, 1)
        selection = selector.currentData() if isinstance(selector, QComboBox) else None
        if not isinstance(selection, int) or not (0 <= selection < len(page.roster.Members)):
            continue
        build = page.roster.Members[selection]
        key = _player_key(build, selection)
        if key in used_players:
            continue
        used_players.add(key)
        selected.append(build)
    return tuple(selected)


def _populate_team_editor_unique(self, table, *, autofill: bool) -> None:
    """Keep legacy editor behavior but stop autofill from cloning real players."""

    assert _ORIGINAL_POPULATE_TEAM_EDITOR is not None
    _ORIGINAL_POPULATE_TEAM_EDITOR(self, table, autofill=autofill)
    if not autofill or self._effective_source_mode() == "Recruitment Plan Only":
        return

    used_players: set[str] = set()
    self._team_combo_signal_guard = True
    try:
        for row in range(table.rowCount()):
            selector = table.cellWidget(row, 1)
            selection = selector.currentData() if isinstance(selector, QComboBox) else None
            if not isinstance(selection, int) or not (0 <= selection < len(self.roster.Members)):
                continue
            build = self.roster.Members[selection]
            key = _player_key(build, selection)
            if key not in used_players:
                used_players.add(key)
                continue

            if self._effective_source_mode() == "Hybrid: Players + Recruitment":
                replacement = selector.findData(f"recruitment:{row}")
            else:
                replacement = selector.findData(None)
            if replacement >= 0:
                selector.setCurrentIndex(replacement)
                self._team_selection_changed(table, row)
    finally:
        self._team_combo_signal_guard = False
    self._update_team_analysis()


def _apply_saved_assignments_to_team_editor(page, prescription) -> None:
    table = page.team_table
    source_mode = page._effective_source_mode()
    page._team_combo_signal_guard = True
    try:
        for row, assignment in enumerate(prescription.assignments):
            selector = table.cellWidget(row, 1)
            if selector is None:
                continue
            selected_index = -1
            if assignment.player_name:
                target_player = assignment.player_name.casefold()
                target_build = str(assignment.source_build_name or "").casefold()
                for index, build in enumerate(page.roster.Members):
                    player = (
                        str(getattr(build, "Name", "") or "").strip()
                        or str(getattr(build, "Gamertag", "") or "").strip()
                        or "Unnamed Player"
                    )
                    build_name = str(getattr(build, "BuildName", "") or "Current Build")
                    if (
                        player.casefold() == target_player
                        and (not target_build or build_name.casefold() == target_build)
                    ):
                        selected_index = selector.findData(index)
                        break
            elif source_mode == "Hybrid: Players + Recruitment":
                selected_index = selector.findData(f"recruitment:{row}")
            else:
                selected_index = selector.findData(None)

            if selected_index >= 0:
                selector.setCurrentIndex(selected_index)
                page._team_selection_changed(table, row)
    finally:
        page._team_combo_signal_guard = False
    page._update_team_analysis()


def _generate_prescription_preview(self, *_args):
    source_mode = self._effective_source_mode()
    saved_builds = tuple(self.roster.Members)
    goal = self.goal_combo.currentText().strip() or "Custom Goal"
    build_constraints = self._prescription_build_constraints()

    if source_mode != "Recruitment Plan Only" and not saved_builds:
        self.current_prescription = None
        self.change_text.setText(
            "No saved builds are available. Add or import builds before asking BFF "
            "to prescribe a saved-player team, or choose Recruitment Plan Only."
        )
        self.status.warning("Generate Best Team needs saved builds; this install currently has 0.")
        return

    if source_mode == "Recruitment Plan Only":
        prescription = generate_prescribed_roster_from_saved_builds(
            name=f"{goal} Prescribed Roster",
            goal=goal,
            slot_labels=tuple(self._role_slots()),
            builds=(),
            scope=self._prescription_scope(),
        )
        prescription = project_slot_build_constraints(
            roster=prescription,
            constraints=tuple(build_constraints.values()),
        )
        self.current_prescription = prescription
        self.change_text.setText("\n".join(format_prescribed_roster_preview(prescription)))
        _apply_saved_assignments_to_team_editor(self, prescription)
        self.status.info(
            f"Generated {goal} recruitment prescription with "
            f"{len(prescription.unresolved)} open requirement(s)."
        )
        return

    # Locked players come from the actual visible Team A selections rather than
    # silently re-autofilling behind the user's back. Without that lock, tanks
    # remain deterministic anchors because there is not yet an authoritative
    # scalar tank objective; healer/DD chairs use the evidence-backed pipeline.
    anchor_builds = (
        _selected_saved_builds(self)
        if self.constraint_boxes["Lock Players"].isChecked()
        else _tank_anchor_builds(self)
    )
    base = generate_prescribed_roster_from_saved_builds(
        name=f"{goal} Prescribed Roster",
        goal=goal,
        slot_labels=tuple(self._role_slots()),
        builds=anchor_builds,
        scope=self._prescription_scope(),
    )
    base = project_slot_build_constraints(
        roster=base,
        constraints=tuple(build_constraints.values()),
    )

    if self.constraint_boxes["Lock Players"].isChecked():
        prescription = base
        pipeline = None
    else:
        evaluator = SavedBuildPrescriptionObjectiveEvaluator(
            build_service=self.build_service,
            database_path=get_data_dir() / "eso.db",
            settings=SavedBuildPrescriptionEvaluationSettings(),
        )
        pipeline = run_automatic_team_prescription_candidate_pipeline(
            roster=base,
            candidates=build_saved_player_prescription_candidates(saved_builds),
            evaluate_objective=evaluator,
            build_constraints_by_slot=build_constraints,
        )
        prescription = pipeline.final_roster

    self.current_prescription = prescription
    self.change_text.setText("\n".join(format_prescribed_roster_preview(prescription)))
    _apply_saved_assignments_to_team_editor(self, prescription)

    saved_count = sum(1 for assignment in prescription.assignments if assignment.player_name)
    unresolved_count = len(prescription.unresolved)
    source_unresolved = 0 if pipeline is None else len(pipeline.unresolved)
    message = (
        f"Generated {goal} prescription: {saved_count} saved player(s) assigned, "
        f"{unresolved_count} roster requirement(s) remain. "
        "Healers use modeled verified-heal potency; DDs use a magical standardized "
        "single-event comparison against 18,200 resistance with Phase 4 sustain gates. "
        "That DD number is not rotation DPS. Tanks remain role-compatible anchors until "
        "an authoritative tank objective exists. Encounter-provider allocation also stays "
        "explicit until this page has a canonical encounter selection."
    )
    if build_constraints:
        ingredients = "; ".join(
            f"{constraint.slot_name}: {constraint.summary}"
            for constraint in build_constraints.values()
        )
        message += f" Required team-slot ingredients preserved: {ingredients}."
    if unresolved_count or source_unresolved:
        self.status.warning(message)
    else:
        self.status.success(message)


def install() -> None:
    global _INSTALLED, _ORIGINAL_POPULATE_TEAM_EDITOR
    if _INSTALLED:
        return
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_POPULATE_TEAM_EDITOR = OptimizationPage._populate_team_editor
    OptimizationPage._populate_team_editor = _populate_team_editor_unique
    OptimizationPage._generate_prescription_preview = _generate_prescription_preview
    _INSTALLED = True
