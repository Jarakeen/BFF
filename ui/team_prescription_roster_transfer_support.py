from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QSizePolicy, QTableWidgetItem

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.team_prescription import PrescriptionDimension
from services.team_prescription_slot_constraints import build_gear_set_names


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
    self.view_combo.currentTextChanged.connect(self._populate_assignment_table)
    self.generated_plan_combo.currentTextChanged.connect(self._generated_plan_changed)
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
