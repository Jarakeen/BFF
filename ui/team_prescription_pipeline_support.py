from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidgetItem,
)

from engine.config import get_data_dir
from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds
from services.team_prescription_pipeline import run_automatic_team_prescription_candidate_pipeline
from services.team_prescription_preview import format_prescribed_roster_preview
from services.team_prescription_promotion import promote_prescribed_slot_to_character_build
from services.team_prescription_saved_build_evaluator import (
    SavedBuildPrescriptionEvaluationSettings,
    SavedBuildPrescriptionObjectiveEvaluator,
    build_saved_player_prescription_candidates,
)
from services.team_role_autofill import normalize_team_role
from services.team_prescription_slot_constraints import (
    build_gear_set_names,
    project_slot_build_constraints,
)


_INSTALLED = False
_ORIGINAL_POPULATE_TEAM_EDITOR = None
_ORIGINAL_BUILD_RECOMMENDATIONS_ROW = None


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


def _goal_short_name(goal: str) -> str:
    known = {
        "Godslayer": "GS",
        "Gryphon Heart": "GH",
        "Hurricane Herald": "HH",
        "Swashbuckler Supreme": "SS",
        "Planebreaker": "PB",
    }
    normalized = str(goal or "").strip()
    if normalized in known:
        return known[normalized]
    words = [word for word in normalized.replace("-", " ").split() if word]
    initials = "".join(word[0].upper() for word in words[:3])
    return initials or "Team"


def _suggested_promoted_build_name(page, assignment) -> str:
    role = assignment.prescribed_role
    if assignment.slot_name.casefold().startswith("main tank"):
        role = "Main Tank"
    elif assignment.slot_name.casefold().startswith("off tank"):
        role = "Off Tank"
    return f"{_goal_short_name(page.goal_combo.currentText())} {role}".strip()


def _character_rows(page) -> tuple[dict, ...]:
    catalog = page.build_service.canonical.catalog_service.load()
    return tuple(
        row for row in catalog.get("characters", ()) if isinstance(row, dict)
    )


def _prescribed_assignments(page):
    prescription = page.current_prescription
    if prescription is None:
        return ()
    return tuple(
        assignment
        for assignment in prescription.assignments
        if assignment.prescribed_build is not None
    )


def _refresh_promotion_controls(page) -> None:
    if not hasattr(page, "prescription_save_slot_combo"):
        return

    current_slot = page.prescription_save_slot_combo.currentData()
    page.prescription_save_slot_combo.blockSignals(True)
    page.prescription_save_slot_combo.clear()
    for assignment in _prescribed_assignments(page):
        source = assignment.source_build_name or assignment.prescribed_role
        page.prescription_save_slot_combo.addItem(
            f"{assignment.slot_name} — {source}",
            assignment.slot_name,
        )
    if current_slot:
        index = page.prescription_save_slot_combo.findData(current_slot)
        if index >= 0:
            page.prescription_save_slot_combo.setCurrentIndex(index)
    page.prescription_save_slot_combo.blockSignals(False)

    page.prescription_target_character_combo.clear()
    for character in _character_rows(page):
        character_id = str(character.get("character_id") or "").strip()
        if not character_id:
            continue
        name = str(character.get("name") or "Unnamed Character")
        eso_class = str(character.get("eso_class") or "Unknown class")
        gamertag = str(character.get("gamertag") or "").strip()
        label = f"{name} — {eso_class}"
        if gamertag:
            label += f" ({gamertag})"
        page.prescription_target_character_combo.addItem(label, character_id)

    _promotion_slot_changed(page)
    enabled = bool(_prescribed_assignments(page)) and page.prescription_target_character_combo.count() > 0
    page.prescription_save_button.setEnabled(enabled)


def _promotion_slot_changed(page, *_args) -> None:
    if not hasattr(page, "prescription_save_slot_combo"):
        return
    slot_name = page.prescription_save_slot_combo.currentData()
    assignment = next(
        (
            item
            for item in _prescribed_assignments(page)
            if item.slot_name == slot_name
        ),
        None,
    )
    if assignment is None:
        page.prescription_build_name_input.setText("")
        return

    page.prescription_build_name_input.setText(
        _suggested_promoted_build_name(page, assignment)
    )

    if assignment.player_name:
        target = assignment.player_name.casefold()
        for index, character in enumerate(_character_rows(page)):
            name = str(character.get("name") or "").strip().casefold()
            gamertag = str(character.get("gamertag") or "").strip().casefold()
            if target in {name, gamertag}:
                character_id = str(character.get("character_id") or "")
                combo_index = page.prescription_target_character_combo.findData(character_id)
                if combo_index >= 0:
                    page.prescription_target_character_combo.setCurrentIndex(combo_index)
                break


def _promote_current_prescription(page, *_args) -> None:
    prescription = page.current_prescription
    if prescription is None:
        page.status.warning("Generate a prescription before saving a prescribed build.")
        return

    slot_name = str(page.prescription_save_slot_combo.currentData() or "").strip()
    character_id = str(page.prescription_target_character_combo.currentData() or "").strip()
    build_name = page.prescription_build_name_input.text().strip()
    if not slot_name or not character_id or not build_name:
        page.status.warning("Choose a prescribed slot, target character, and new build name.")
        return

    try:
        result = promote_prescribed_slot_to_character_build(
            catalog_service=page.build_service.canonical.catalog_service,
            roster=prescription,
            slot_name=slot_name,
            character_id=character_id,
            build_name=build_name,
        )
        # Canonical catalog is authoritative. Reload it and explicitly sync the
        # compatibility builds.json mirror so every existing page/tool sees the
        # new build through the same BuildService boundary.
        page.roster = page.build_service.load()
        page.build_service.save(page.roster)
    except Exception as exc:
        page.status.error(f"Could not save prescribed build: {exc}")
        return

    page._populate_available()
    page.status.success(
        f"Saved {result.build_name} as a new build for the selected character. "
        "The source prescription and existing builds were not overwritten."
    )
    _refresh_promotion_controls(page)


def _recommendation_reason(prescription, assignment) -> str:
    for change in assignment.changes:
        if change.reason:
            return change.reason
    slot_prefix = assignment.slot_name.casefold()
    for assumption in prescription.assumptions:
        if slot_prefix in assumption.casefold():
            return assumption
    if assignment.prescribed_build is not None:
        return "Complete build snapshot preserved from the ranked prescription candidate."
    return "No complete prescribed build is available for this slot."


def _render_prescription_details(page, prescription) -> None:
    gear_rows: list[tuple[str, str, str]] = []
    skill_rows: list[tuple[str, str, str, str]] = []

    for assignment in prescription.assignments:
        build = assignment.prescribed_build
        if build is None:
            continue
        subject = assignment.player_name or assignment.slot_name
        source = build.BuildName.strip() or assignment.source_build_name or "Prescribed Build"
        sets = build_gear_set_names(build)
        gear_summary = " + ".join(sets) if sets else "No named gear sets in snapshot"
        detail_bits = [source]
        if build.EsoClass:
            detail_bits.append(build.EsoClass)
        if build.Race:
            detail_bits.append(build.Race)
        if build.Mundus:
            detail_bits.append(build.Mundus)
        if build.Food:
            detail_bits.append(build.Food)
        gear_rows.append(
            (
                subject,
                f"{gear_summary} | " + " | ".join(detail_bits),
                _recommendation_reason(prescription, assignment),
            )
        )

        front = " / ".join(str(value).strip() for value in build.FrontBarSkills if str(value).strip())
        back = " / ".join(str(value).strip() for value in build.BackBarSkills if str(value).strip())
        bars: list[str] = []
        if front:
            bars.append(f"Front: {front}")
        if back:
            bars.append(f"Back: {back}")
        if build.Potion:
            bars.append(f"Potion: {build.Potion}")
        skill_rows.append(
            (
                subject,
                " | ".join(bars) if bars else "No skill bars in snapshot",
                "—",
                _recommendation_reason(prescription, assignment),
            )
        )

    if not gear_rows:
        gear_rows = [("—", "No complete prescribed build snapshots yet", "Open slots remain unresolved")]
    if not skill_rows:
        skill_rows = [("—", "No complete prescribed skill bars yet", "—", "Open slots remain unresolved")]

    page.gear_table.setRowCount(len(gear_rows))
    for row, values in enumerate(gear_rows):
        for column, value in enumerate(values):
            page.gear_table.setItem(row, column, QTableWidgetItem(str(value)))

    page.skill_table.setRowCount(len(skill_rows))
    for row, values in enumerate(skill_rows):
        for column, value in enumerate(values):
            page.skill_table.setItem(row, column, QTableWidgetItem(str(value)))


def _build_recommendations_row_completed(self) -> None:
    assert _ORIGINAL_BUILD_RECOMMENDATIONS_ROW is not None
    _ORIGINAL_BUILD_RECOMMENDATIONS_ROW(self)

    save_row = QHBoxLayout()
    save_row.setSpacing(8)
    save_row.addWidget(QLabel("SAVE PRESCRIBED BUILD"))

    self.prescription_save_slot_combo = QComboBox()
    self.prescription_save_slot_combo.setMinimumWidth(150)
    save_row.addWidget(self.prescription_save_slot_combo)

    self.prescription_target_character_combo = QComboBox()
    self.prescription_target_character_combo.setMinimumWidth(170)
    save_row.addWidget(self.prescription_target_character_combo)

    self.prescription_build_name_input = QLineEdit()
    self.prescription_build_name_input.setPlaceholderText("GH Healer")
    self.prescription_build_name_input.setMinimumWidth(120)
    save_row.addWidget(self.prescription_build_name_input)

    self.prescription_save_button = QPushButton("Save as New Build")
    self.prescription_save_button.setEnabled(False)
    save_row.addWidget(self.prescription_save_button)

    self.change_card.addLayout(save_row)
    self.prescription_save_slot_combo.currentIndexChanged.connect(
        lambda *_: _promotion_slot_changed(self)
    )
    self.prescription_save_button.clicked.connect(
        lambda *_: _promote_current_prescription(self)
    )


def _finalize_prescription_ui(page, prescription) -> None:
    page.current_prescription = prescription
    page.change_text.setText("\n".join(format_prescribed_roster_preview(prescription)))
    _apply_saved_assignments_to_team_editor(page, prescription)
    _render_prescription_details(page, prescription)
    _refresh_promotion_controls(page)


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
        _render_prescription_details(
            self,
            generate_prescribed_roster_from_saved_builds(
                name=f"{goal} Prescribed Roster",
                goal=goal,
                slot_labels=tuple(self._role_slots()),
                builds=(),
                scope=self._prescription_scope(),
            ),
        )
        _refresh_promotion_controls(self)
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
        _finalize_prescription_ui(self, prescription)
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

    _finalize_prescription_ui(self, prescription)

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
    global _INSTALLED, _ORIGINAL_POPULATE_TEAM_EDITOR, _ORIGINAL_BUILD_RECOMMENDATIONS_ROW
    if _INSTALLED:
        return
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_POPULATE_TEAM_EDITOR = OptimizationPage._populate_team_editor
    _ORIGINAL_BUILD_RECOMMENDATIONS_ROW = OptimizationPage._build_recommendations_row
    OptimizationPage._populate_team_editor = _populate_team_editor_unique
    OptimizationPage._build_recommendations_row = _build_recommendations_row_completed
    OptimizationPage._generate_prescription_preview = _generate_prescription_preview
    _INSTALLED = True
