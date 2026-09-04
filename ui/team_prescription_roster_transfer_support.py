from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.team_prescription import PrescriptionDimension
from services.team_prescription_slot_constraints import build_gear_set_names
from services.team_prescription_template_inspector import find_team_template_inspection


_INSTALLED = False
_ORIGINAL_BUILD_RECOMMENDATIONS_ROW = None
_ORIGINAL_FINALIZE = None
_ORIGINAL_ROSTER_INIT = None
_ORIGINAL_ROSTER_POPULATE = None


def _change_value(assignment, dimension: PrescriptionDimension) -> str:
    change = assignment.change_for(dimension)
    return "" if change is None else str(change.prescribed_value or "").strip()


def _saved_build_for_assignment(page, assignment):
    target_player = str(assignment.player_name or "").strip().casefold()
    target_build = str(assignment.source_build_name or "").strip().casefold()
    for build in page.roster.Members:
        player = (
            str(getattr(build, "Name", "") or "").strip()
            or str(getattr(build, "Gamertag", "") or "").strip()
        ).casefold()
        build_name = str(getattr(build, "BuildName", "") or "").strip().casefold()
        if player == target_player and (not target_build or build_name == target_build):
            return build
    return None


def prescription_plan_slots(page) -> tuple[GeneratedRosterPlanSlot, ...]:
    """Project the generated prescription itself into a persistent roster plan."""

    prescription = getattr(page, "current_prescription", None)
    if prescription is None:
        return ()

    rows: list[GeneratedRosterPlanSlot] = []
    for assignment in prescription.assignments:
        prescribed = assignment.prescribed_build
        source_build = (
            _saved_build_for_assignment(page, assignment)
            if assignment.player_name
            else None
        )
        build = prescribed or source_build

        eso_class = ""
        build_name = str(assignment.source_build_name or "").strip()
        character_name = ""
        gear_summary = ""
        if build is not None:
            eso_class = str(getattr(build, "EsoClass", "") or "").strip()
            build_name = str(getattr(build, "BuildName", "") or build_name).strip()
            character_name = (
                str(getattr(build, "CharacterName", "") or "").strip()
                or str(getattr(build, "Name", "") or "").strip()
            )
            gear_summary = " + ".join(build_gear_set_names(build))

        eso_class = eso_class or _change_value(
            assignment, PrescriptionDimension.CLASS
        )
        build_name = build_name or _change_value(
            assignment, PrescriptionDimension.BUILD
        )
        gear_summary = gear_summary or _change_value(
            assignment, PrescriptionDimension.GEAR
        )

        if assignment.player_name:
            kind = "saved"
            player_name = assignment.player_name
        elif assignment.has_candidate_recommendation:
            kind = "prescribed_recruit"
            player_name = "Recruitment Needed"
        else:
            kind = "open_recruit"
            player_name = "Recruitment Needed"

        unresolved = "; ".join(
            str(item).strip() for item in assignment.unresolved if str(item).strip()
        )
        rows.append(
            GeneratedRosterPlanSlot(
                slot_name=assignment.slot_name,
                kind=kind,
                player_name=player_name,
                character_name=character_name,
                eso_class=eso_class or "Any class",
                build_name=build_name or "Open requirement",
                gear_summary=gear_summary,
                unresolved=unresolved,
            )
        )
    return tuple(rows)


def concise_prescription_preview(prescription) -> str:
    """Keep the preview readable; full evidence remains in recommendation tables."""

    lines = [prescription.name]
    saved = prescribed = open_count = 0
    for assignment in prescription.assignments:
        if assignment.player_name:
            saved += 1
            label = assignment.player_name
            if assignment.source_build_name:
                label += f" — {assignment.source_build_name}"
        elif assignment.has_candidate_recommendation:
            prescribed += 1
            cls = _change_value(assignment, PrescriptionDimension.CLASS)
            build_name = (
                assignment.source_build_name
                or _change_value(assignment, PrescriptionDimension.BUILD)
            )
            detail = " • ".join(value for value in (cls, build_name) if value)
            label = "RECRUIT" + (f" — {detail}" if detail else "")
        else:
            open_count += 1
            cls = _change_value(assignment, PrescriptionDimension.CLASS)
            label = "RECRUIT" + (f" — {cls}" if cls else " — unresolved")
        lines.append(f"{assignment.slot_name}: {label}")

    lines.append(
        f"Saved players: {saved}   Prescribed recruits: {prescribed}   "
        f"Still unresolved: {open_count}"
    )
    if prescription.unresolved:
        lines.append(
            "Unresolved evidence remains in the recommendation details; "
            "BFF did not invent missing build data."
        )
    return "\n".join(lines)


def _build_recommendations_row_bounded(self) -> None:
    assert _ORIGINAL_BUILD_RECOMMENDATIONS_ROW is not None
    _ORIGINAL_BUILD_RECOMMENDATIONS_ROW(self)
    self.change_text.setMinimumWidth(0)
    self.change_text.setMinimumHeight(90)
    self.change_text.setMaximumHeight(220)
    self.change_text.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Preferred,
    )
    self.change_text.setWordWrap(True)
    self.change_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    self.change_card.setMinimumWidth(0)
    self.change_card.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )


def _finalize_concise(page, prescription) -> None:
    assert _ORIGINAL_FINALIZE is not None
    _ORIGINAL_FINALIZE(page, prescription)
    page.change_text.setText(concise_prescription_preview(prescription))


def _selected_template_inspection(page):
    if (
        page.view_combo.currentText() != "Generated Team"
        or page.assignment_table.currentRow() < 0
    ):
        return None
    row = page.assignment_table.currentRow()
    slot_item = page.assignment_table.item(row, 1)
    class_item = page.assignment_table.item(row, 2)
    build_item = page.assignment_table.item(row, 3)
    if slot_item is None or build_item is None:
        return None
    return find_team_template_inspection(
        data_dir=get_data_dir(),
        slot_name=slot_item.text(),
        build_name=build_item.text(),
        eso_class=class_item.text() if class_item is not None else "",
    )


def _update_view_template_button(page, *_args) -> None:
    if not hasattr(page, "view_template_button"):
        return
    try:
        inspection = _selected_template_inspection(page)
    except Exception as exc:
        page.view_template_button.setEnabled(False)
        page.view_template_button.setToolTip(f"Template evidence could not be loaded: {exc}")
        return
    page.view_template_button.setEnabled(inspection is not None)
    page.view_template_button.setToolTip(
        "Show exactly what BFF knows about this generated template."
        if inspection is not None
        else "Select a generated recruit row backed by a team template."
    )


def _inspection_text(inspection) -> str:
    lines = [
        inspection.name,
        "",
        f"TYPE: {inspection.template_kind}",
        f"CLASS: {inspection.eso_class}",
        f"ROLE: {inspection.role}",
        f"COMPLETE BUILD: {'Yes' if inspection.complete_build else 'No'}",
        f"TEMPLATE ID: {inspection.template_id}",
    ]
    if inspection.catalog_version:
        lines.append(f"CATALOG: {inspection.catalog_version}")
    if inspection.game_update:
        lines.append(f"GAME UPDATE: {inspection.game_update}")
    if inspection.trial_name:
        lines.append(f"TRIAL: {inspection.trial_name}")
    if inspection.encounter_name:
        lines.append(f"ENCOUNTER: {inspection.encounter_name}")
    if inspection.observed_player_name:
        lines.append(f"OBSERVED PLAYER: {inspection.observed_player_name}")
    if inspection.report_code:
        lines.append(f"REPORT: {inspection.report_code}")
    if inspection.fight_id:
        lines.append(f"FIGHT: {inspection.fight_id}")
    lines.extend(
        [
            "",
            "SOURCE",
            inspection.source_name or "Unresolved source",
            inspection.source_url or "No source URL recorded",
            f"Retrieved: {inspection.retrieved_at or 'unresolved'}",
            "",
            "KNOWN",
        ]
    )
    lines.extend(
        f"✓ {field}" for field in (inspection.known_fields or ("class", "role"))
    )
    if inspection.gear_sets:
        lines.extend(("", "GEAR SETS", *[f"• {value}" for value in inspection.gear_sets]))
    if inspection.skills:
        lines.extend(("", "SKILLS", *[f"• {value}" for value in inspection.skills]))
    if inspection.mundus:
        lines.extend(("", "MUNDUS", inspection.mundus))
    lines.extend(("", "UNKNOWN / UNRESOLVED"))
    if inspection.unknown_fields:
        lines.extend(f"• {value}" for value in inspection.unknown_fields)
    else:
        lines.append("None recorded.")
    if not inspection.complete_build:
        lines.extend(
            (
                "",
                "BOUNDARY",
                "This is evidence for a team prescription, not a complete saved build. "
                "BFF will not invent missing gear, traits, CP, skills, food, or other fields.",
            )
        )
    return "\n".join(lines)


def _show_selected_template(page, *_args) -> None:
    try:
        inspection = _selected_template_inspection(page)
    except Exception as exc:
        page.status.error(f"Could not inspect team template: {exc}")
        return
    if inspection is None:
        page.status.info("Select a generated recruit row backed by a team template first.")
        return

    dialog = QDialog(page)
    dialog.setWindowTitle(f"Team Template • {inspection.name}")
    dialog.resize(680, 560)
    layout = QVBoxLayout(dialog)
    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(_inspection_text(inspection))
    layout.addWidget(text, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.clicked.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()


def _roster_init_with_generated_plans(self, parent=None) -> None:
    assert _ORIGINAL_ROSTER_INIT is not None
    _ORIGINAL_ROSTER_INIT(self, parent)
    self.generated_plan_service = GeneratedRosterPlanService(
        EsoDatabase(get_data_dir() / "eso.db")
    )
    if self.view_combo.findText("Generated Team") < 0:
        self.view_combo.addItem("Generated Team")
    self.generated_plan_combo = QComboBox()
    self.generated_plan_combo.setMinimumWidth(160)
    self.generated_plan_combo.setMaximumWidth(320)
    self.header.add_context_widget(self._context_field("GENERATED ROSTER", self.generated_plan_combo))
    self.view_template_button = QPushButton("View Template")
    self.view_template_button.setEnabled(False)
    self.header.add_context_widget(self.view_template_button)
    self.view_combo.currentTextChanged.connect(self._populate_assignment_table)
    self.view_combo.currentTextChanged.connect(lambda *_: _update_view_template_button(self))
    self.generated_plan_combo.currentTextChanged.connect(self._generated_plan_changed)
    self.assignment_table.itemSelectionChanged.connect(
        lambda: _update_view_template_button(self)
    )
    self.assignment_table.itemDoubleClicked.connect(
        lambda *_: _show_selected_template(self)
        if _selected_template_inspection(self) is not None
        else None
    )
    self.view_template_button.clicked.connect(lambda *_: _show_selected_template(self))
    self._refresh_generated_plan_choices()


def _refresh_generated_plan_choices(page, selected: str | None = None) -> None:
    if not hasattr(page, "generated_plan_combo"):
        return
    names = page.generated_plan_service.list_plan_names()
    current = str(selected or page.generated_plan_combo.currentText() or "").strip()
    page.generated_plan_combo.blockSignals(True)
    page.generated_plan_combo.clear()
    page.generated_plan_combo.addItems(list(names))
    if current:
        index = page.generated_plan_combo.findText(current)
        if index >= 0:
            page.generated_plan_combo.setCurrentIndex(index)
    page.generated_plan_combo.blockSignals(False)


def _generated_plan_changed(page, *_args) -> None:
    if page.view_combo.currentText() == "Generated Team":
        page._populate_assignment_table()


def _render_generated_summary(page, plan) -> None:
    tanks = sum(1 for slot in plan.slots if "tank" in slot.slot_name.casefold())
    healers = sum(1 for slot in plan.slots if "heal" in slot.slot_name.casefold())
    dds = max(0, len(plan.slots) - tanks - healers)
    saved = sum(1 for slot in plan.slots if slot.kind == "saved")
    prescribed = sum(1 for slot in plan.slots if slot.kind == "prescribed_recruit")
    open_count = sum(1 for slot in plan.slots if slot.kind == "open_recruit")

    page.attention_card.clear()
    if open_count:
        page.attention_card.addWidget(
            QLabel(f"⚠  {open_count} generated slot(s) still need a concrete class/build prescription.")
        )
    elif prescribed:
        page.attention_card.addWidget(
            QLabel(f"◈  {prescribed} prescribed recruit slot(s) need players assigned.")
        )
    else:
        page.attention_card.addWidget(QLabel("✓  Generated team is fully assigned."))

    page.team_card.clear()
    page.team_card.addWidget(
        QLabel(
            f"Tanks      {tanks}\n"
            f"Healers    {healers}\n"
            f"Damage     {dds}\n"
            f"Saved      {saved}\n"
            f"Recruits   {prescribed + open_count}\n\n"
            f"Plan: {plan.name}"
        )
    )


def _render_generated_plan(page) -> None:
    name = page.generated_plan_combo.currentText().strip()
    plan = (
        page.generated_plan_service.load_plan(name)
        if name
        else page.generated_plan_service.latest_plan()
    )
    page.assignment_table.setRowCount(0)
    if plan is None:
        page.status.info("No generated team has been sent from Team Optimization yet.")
        _update_view_template_button(page)
        return

    for slot in plan.slots:
        row = page.assignment_table.rowCount()
        page.assignment_table.insertRow(row)
        is_recruit = slot.kind != "saved"
        notes = slot.unresolved
        if not notes:
            notes = (
                "Generated recruitment prescription"
                if is_recruit
                else "Saved player selected by Team Optimization"
            )
        values = (
            slot.player_name,
            slot.slot_name,
            slot.eso_class or "Any class",
            slot.build_name or "Open requirement",
            "Generated team slot",
            "Recruit / qualify candidate" if is_recruit else page._secondary_assignment(slot.slot_name),
            slot.gear_summary or "—",
            notes,
            "OPEN" if is_recruit else "✓",
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column in {0, 1, 2, 3, 8}:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            page.assignment_table.setItem(row, column, item)

    _render_generated_summary(page, plan)
    _update_view_template_button(page)
    page.status.success(
        f"Generated roster loaded: {plan.name} • {plan.goal} • "
        f"{len(plan.slots)} slot(s)."
    )


def _populate_assignment_table_with_generated_plan(self, *_args) -> None:
    if (
        hasattr(self, "view_combo")
        and self.view_combo.currentText() == "Generated Team"
        and hasattr(self, "generated_plan_service")
    ):
        _render_generated_plan(self)
        return
    assert _ORIGINAL_ROSTER_POPULATE is not None
    _ORIGINAL_ROSTER_POPULATE(self, *_args)
    if hasattr(self, "view_template_button"):
        self.view_template_button.setEnabled(False)
    # Switching away from Generated Team restores the canonical roster summary.
    if hasattr(self, "team_card") and hasattr(self, "attention_card"):
        self._refresh_summary_cards()


def _send_generated_prescription_to_roster(window) -> None:
    optimization_page = window.pages.get("console:6")
    prescription = getattr(optimization_page, "current_prescription", None)
    if prescription is None:
        optimization_page.status.warning(
            "Generate Best Team first. Send to Roster uses the generated prescription, "
            "not whatever happens to be visible in the dropdowns."
        )
        return

    slots = prescription_plan_slots(optimization_page)
    if not slots:
        optimization_page.status.warning("The generated prescription contains no roster slots.")
        return

    roster_page = window.pages["roster_page"]
    plan = roster_page.generated_plan_service.save_plan(
        name=prescription.name,
        goal=prescription.goal,
        difficulty=optimization_page.difficulty_combo.currentText(),
        slots=slots,
    )
    _refresh_generated_plan_choices(roster_page, plan.name)
    roster_page.view_combo.setCurrentText("Generated Team")
    roster_page.tabs.setCurrentIndex(0)
    _render_generated_plan(roster_page)

    unresolved = sum(1 for slot in slots if slot.kind == "open_recruit")
    prescribed = sum(1 for slot in slots if slot.kind == "prescribed_recruit")
    saved = sum(1 for slot in slots if slot.kind == "saved")
    optimization_page.status.success(
        f"Sent {plan.name} to Roster: {saved} saved player(s), "
        f"{prescribed} prescribed recruit(s), {unresolved} unresolved recruit slot(s)."
    )
    window.show_page("roster_page")


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_BUILD_RECOMMENDATIONS_ROW, _ORIGINAL_FINALIZE
    global _ORIGINAL_ROSTER_INIT, _ORIGINAL_ROSTER_POPULATE
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage
    from ui.roster_page import RosterPage
    import ui.team_prescription_pipeline_support as pipeline_support
    from ui.main_window import MainWindow

    _ORIGINAL_BUILD_RECOMMENDATIONS_ROW = OptimizationPage._build_recommendations_row
    OptimizationPage._build_recommendations_row = _build_recommendations_row_bounded

    _ORIGINAL_FINALIZE = pipeline_support._finalize_prescription_ui
    pipeline_support._finalize_prescription_ui = _finalize_concise

    _ORIGINAL_ROSTER_INIT = RosterPage.__init__
    _ORIGINAL_ROSTER_POPULATE = RosterPage._populate_assignment_table
    RosterPage.__init__ = _roster_init_with_generated_plans
    RosterPage._refresh_generated_plan_choices = _refresh_generated_plan_choices
    RosterPage._generated_plan_changed = _generated_plan_changed
    RosterPage._populate_assignment_table = _populate_assignment_table_with_generated_plan

    MainWindow._send_optimized_team_to_roster = _send_generated_prescription_to_roster
    _INSTALLED = True
