from __future__ import annotations

from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds
from services.team_prescription_pipeline import run_automatic_team_prescription_candidate_pipeline
from services.team_prescription_preview import format_prescribed_roster_preview
from services.team_prescription_saved_build_evaluator import (
    SavedBuildPrescriptionEvaluationSettings,
    SavedBuildPrescriptionObjectiveEvaluator,
    build_saved_player_prescription_candidates,
)
from services.team_role_autofill import normalize_team_role


_INSTALLED = False


def _tank_anchor_builds(page):
    return tuple(
        build
        for build in page.roster.Members
        if normalize_team_role(getattr(build, "Role", "")) == "tank"
    )


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
    self._generate_preview()
    source_mode = self._effective_source_mode()
    saved_builds = tuple(self.roster.Members)
    goal = self.goal_combo.currentText().strip() or "Custom Goal"

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
        self.current_prescription = prescription
        self.change_text.setText("\n".join(format_prescribed_roster_preview(prescription)))
        _apply_saved_assignments_to_team_editor(self, prescription)
        self.status.info(
            f"Generated {goal} recruitment prescription with "
            f"{len(prescription.unresolved)} open requirement(s)."
        )
        return

    # Lock Players preserves the existing deterministic saved anchors. Without
    # that lock, tanks remain anchors because BFF does not yet have an authoritative
    # scalar tank-ranking objective; healer/DD chairs are left open for the real
    # objective pipeline below.
    anchor_builds = (
        saved_builds
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

    if self.constraint_boxes["Lock Players"].isChecked():
        prescription = base
        pipeline = None
    else:
        evaluator = SavedBuildPrescriptionObjectiveEvaluator(
            build_service=self.build_service,
            database_path=self.build_service.canonical.database_path,
            settings=SavedBuildPrescriptionEvaluationSettings(),
        )
        pipeline = run_automatic_team_prescription_candidate_pipeline(
            roster=base,
            candidates=build_saved_player_prescription_candidates(saved_builds),
            evaluate_objective=evaluator,
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
        "Healers use modeled verified-heal potency; DDs use the canonical standardized "
        "single-event damage comparison with Phase 4 sustain gates. Tanks are not ranked "
        "until an authoritative tank objective exists."
    )
    if unresolved_count or source_unresolved:
        self.status.warning(message)
    else:
        self.status.success(message)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from ui.optimization_page import OptimizationPage

    OptimizationPage._generate_prescription_preview = _generate_prescription_preview
    _INSTALLED = True
