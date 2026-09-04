from __future__ import annotations

from services.generated_roster_plan_service import GeneratedRosterPlanSlot


_INSTALLED = False
_ORIGINAL_INIT = None


def _remove_combo_text(combo, text: str) -> None:
    index = combo.findText(text)
    if index >= 0:
        combo.removeItem(index)


def _refocus_optimization_ui(page) -> None:
    """Remove composition/prescription controls from the Optimization surface.

    Composition creation is moving upstream to Comp Builder. Optimization remains
    responsible for auditing, improving, and comparing teams that already exist.
    The prescription services stay installed because Comp Builder and roster
    optimization can reuse that tested machinery without exposing it here.
    """

    page.header.title.setText("Team Optimization")
    page.header.subtitle.setText(
        "Audit, improve, and compare an existing team. Composition creation lives in Comp Builder."
    )
    page.header.department.setText("RAID ENGINE • OPTIMIZATION")

    # Keep Audit / Optimize / Compare. Recruitment planning belongs to Comp Builder.
    for index in range(page.mode_tabs.count() - 1, -1, -1):
        title = page.mode_tabs.tabText(index)
        if title == "Recruitment Plan":
            page.mode_tabs.removeTab(index)
        elif title == "Build Best Team":
            page.mode_tabs.setTabText(index, "Optimize Team")

    # The old action generated a new composition/prescription from scratch. That is
    # precisely the responsibility being moved out of this page.
    if hasattr(page, "generate_button"):
        page.generate_button.hide()
        page.generate_button.setEnabled(False)

    # Prescription preview and prescribed-build promotion are orchestration UI for
    # the old flow. Keep the underlying widgets alive for installed compatibility
    # layers, but remove the card from the user's Optimization workspace.
    if hasattr(page, "change_card"):
        page.change_card.hide()
        page.change_card.setMaximumHeight(0)

    # Recruitment-only source is composition planning rather than optimization.
    if hasattr(page, "team_source_combo"):
        _remove_combo_text(page.team_source_combo, "Recruitment Plan Only")

    # Existing-team optimization may still include open recruit chairs, so Hybrid
    # remains available alongside Saved Players Only.
    page.current_prescription = None
    page.status.info(
        f"Optimization ready • {len(page.roster.Members)} saved build(s) available. "
        "Use this page to audit, improve, or compare an existing team."
    )


def _init_refocused(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)
    _refocus_optimization_ui(self)


def _send_visible_optimization_team_to_roster(window) -> None:
    """Persist the visible Optimization team as a generated roster plan.

    This intentionally ignores ``current_prescription``. Once composition creation
    moves to Comp Builder, the Optimization page's source of truth is the team the
    user is actually viewing/editing (Team A or Team B).
    """

    optimization_page = window.pages.get("console:6")
    plan_rows = window._current_optimized_team_plan()
    if not plan_rows:
        if optimization_page is not None:
            optimization_page.status.warning(
                "No team slots are selected. Load or assemble a team before sending it to Roster."
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

    _ORIGINAL_INIT = OptimizationPage.__init__
    OptimizationPage.__init__ = _init_refocused
    MainWindow._send_optimized_team_to_roster = _send_visible_optimization_team_to_roster
    _INSTALLED = True
