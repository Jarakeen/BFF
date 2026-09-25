from __future__ import annotations

"""Register raid-planning surfaces with the existing application window.

This module is the explicit application-composition boundary for the rebuilt
raid-lead workspace. It keeps long-lived engine ownership intact while exposing
the Urban Wilderness RAID workflow as Roster -> Plans -> Assignments ->
Readiness -> Live Raid.
"""

import warnings
from types import SimpleNamespace

_INSTALLED = False


def _install_canonical_sidebar_routes() -> None:
    """Reorder the existing workflow groups without changing their membership."""
    from ui.components import foundry_sidebar

    def existing_dict(label: str):
        for section in foundry_sidebar.CORE_NAV_SECTIONS:
            if isinstance(section, dict) and section.get("label") == label:
                return section
        return None

    collectibles = existing_dict("Collectibles")
    tools = existing_dict("Tools") or existing_dict("Tool")

    sections: list = [
        {
            "label": "Raid",
            "children": [
                ("Roster", "roster_workspace"),
                ("Raid Plans", "raid_plans"),
                ("Assignments", "assignments"),
                ("Readiness", "readiness"),
                ("Live Raid", "live_raid"),
            ],
        },
        {
            "label": "Team",
            "children": [
                ("Coverage", "console:7"),
                ("Comp Builder", "comp_builder"),
                ("Optimizer Adviser", "console:6"),
                ("Finch Collaboration", "finch_collaboration"),
            ],
        },
        {
            "label": "Build",
            "children": [
                ("Builds", "console:2"),
                ("Rotation Builder", "rotations"),
                ("Extreme Builder", "extreme_optimization"),
            ],
        },
        {
            "label": "Encounter",
            "children": [
                ("Encounters", "console:1"),
                ("Mechanics & Timelines", "console:4"),
            ],
        },
        {
            "label": "Review",
            "children": [
                ("Top Gear", "console:3"),
                ("Brittle Uptime", "brittle_uptime"),
            ],
        },
        {"label": "Achievement", "page": "achievements", "children": []},
    ]
    if collectibles is not None:
        sections.append(collectibles)
    if tools is not None:
        normalized_tools = dict(tools)
        normalized_tools["label"] = "Tools"
        sections.append(normalized_tools)
    sections.append({"label": "Settings", "page": "settings", "children": []})

    foundry_sidebar.CORE_NAV_SECTIONS[:] = sections


def _install_safe_dashboard_rewire() -> None:
    """Avoid PySide's noisy RuntimeWarning when a button has no slots to remove."""
    from ui import raid_engine_dashboard_polish_support as polish

    def safe_rewire(button, callback) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"libpyside: Failed to disconnect.*",
                category=RuntimeWarning,
            )
            try:
                button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
        button.clicked.connect(lambda *_: callback())

    polish._rewire_button = safe_rewire


def _open_dashboard_help(window) -> None:
    settings = window.pages.get("settings")
    if settings is None:
        return
    window.show_page("settings")
    help_page = getattr(settings, "help_page", None)
    help_index = getattr(settings, "help_section_index", None)
    if help_page is not None and help_index is not None:
        settings._show_section(help_index)
        help_page.show_topic("comp_builder")


def _open_saved_plan_assignments(window, plan_id: str) -> None:
    """Open Assignments on one exact persisted Raid Plan."""
    assignments = window.pages.get("assignments")
    if assignments is None or not hasattr(assignments, "load_plan_by_id"):
        return
    if not assignments.load_plan_by_id(plan_id):
        return
    window.show_page("assignments")


def _open_raid_plan_map(window, plan_id: str) -> None:
    encounters = window.pages.get("console:1")
    if encounters is None:
        return
    window.show_page("console:1")
    opener = getattr(encounters, "open_saved_plan_map", None)
    if callable(opener):
        opener(str(plan_id or "").strip())
        return

    combo = getattr(encounters, "raid_plan_combo", None)
    if combo is not None:
        index = combo.findData(str(plan_id or "").strip())
        if index >= 0:
            combo.setCurrentIndex(index)

def _open_raid_plan_coverage(window, plan) -> None:
    coverage = window.pages.get("console:7")
    if coverage is None or not hasattr(coverage, "set_raid_plan_scope"):
        return
    coverage.set_raid_plan_scope(plan)
    window.show_page("console:7")


def _open_raid_plan_rotation(window, plan, seat_id: str) -> None:
    rotation = window.pages.get("rotations")
    if rotation is None:
        return
    from ui.raid_plan_rotation_handoff_support import bind_raid_plan_rotation_page

    try:
        bind_raid_plan_rotation_page(rotation, raid_plan=plan, seat_id=seat_id)
    except (OSError, TypeError, ValueError) as exc:
        raid_plans = window.pages.get("raid_plans")
        status = getattr(raid_plans, "status", None)
        if status is not None:
            status.warning(f"Could not open Raid Plan spot in Rotation: {exc}")
        return
    window.show_page("rotations")


def _open_raid_plan_adviser(window, plan) -> None:
    adviser = window.pages.get("console:6")
    if adviser is None or not hasattr(adviser, "set_raid_plan_adviser_scope"):
        return
    try:
        adviser.set_raid_plan_adviser_scope(plan)
    except (OSError, TypeError, ValueError) as exc:
        raid_plans = window.pages.get("raid_plans")
        status = getattr(raid_plans, "status", None)
        if status is not None:
            status.warning(f"Could not review Raid Plan in Optimizer Adviser: {exc}")
        return
    window.show_page("console:6")



def _bind_plan_comp_builder(window, source_page) -> bool:
    """Bind the current Raid Plan into Comp Builder without navigating."""
    comp = window.pages.get("comp_builder")
    if comp is None or not hasattr(comp, "apply_roster_team_context"):
        return False

    try:
        has_pending = getattr(source_page, "has_pending_changes", None)
        if callable(has_pending) and has_pending():
            status = getattr(source_page, "status", None)
            if status is not None:
                status.warning("Save or discard Raid Plan changes before opening Comp Builder.")
            return False
        plan = getattr(source_page, "_loaded_plan_snapshot", None)
        if plan is None:
            status = getattr(source_page, "status", None)
            if status is not None:
                status.warning("Save the Raid Plan before opening Comp Builder.")
            return False
        repository = getattr(source_page, "plan_repository", None)
        verified_plan = repository.get(plan.plan_id) if repository is not None else None
        if verified_plan is None or verified_plan != plan:
            status = getattr(source_page, "status", None)
            if status is not None:
                status.warning(
                    "The loaded Raid Plan does not match its saved checkpoint. Reload the plan before opening Comp Builder."
                )
            return False
        plan = verified_plan
    except (AttributeError, OSError, TypeError, ValueError):
        return False

    trial_combo = getattr(source_page, "trial_combo", None)
    trial_name = (
        str(trial_combo.currentText() or "").strip()
        if trial_combo is not None
        else ""
    )
    difficulty_combo = getattr(source_page, "difficulty_combo", None)
    difficulty = (
        str(difficulty_combo.currentText() or "").strip()
        if difficulty_combo is not None
        else ""
    )

    if trial_name:
        from ui.comp_builder_page import GOAL_TRIALS

        matching_goals = [
            goal
            for goal, mapped_trial in GOAL_TRIALS.items()
            if str(mapped_trial or "").strip().casefold() == trial_name.casefold()
        ]
        current_goal = str(comp.goal_combo.currentText() or "").strip()
        current_trial = str(GOAL_TRIALS.get(current_goal, "") or "").strip()
        preferred_goal = (
            current_goal
            if current_trial.casefold() == trial_name.casefold()
            else matching_goals[0] if matching_goals else ""
        )
        if preferred_goal:
            index = comp.goal_combo.findText(preferred_goal)
            if index >= 0:
                comp.goal_combo.setCurrentIndex(index)
    if difficulty:
        index = comp.difficulty_combo.findText(difficulty)
        if index >= 0:
            comp.difficulty_combo.setCurrentIndex(index)

    canonical_seats = (
        "Tank 1", "Tank 2", "Healer 1", "Healer 2",
        "DD 1", "DD 2", "DD 3", "DD 4",
        "DD 5", "DD 6", "DD 7", "DD 8",
    )
    members = tuple(
        SimpleNamespace(
            Id=getattr(member, "roster_member_id", None),
            CanonicalPlayerId=str(getattr(member, "player_id", "") or "").strip(),
            CanonicalCharacterId=str(getattr(member, "character_id", "") or "").strip(),
            RaidSeatId=next(
                (
                    seat
                    for seat in canonical_seats
                    if "-".join(seat.casefold().split())
                    == str(getattr(member, "seat_id", "") or "").strip().casefold()
                ),
                str(getattr(member, "seat_id", "") or "").strip(),
            ),
            PlayerName=(
                str(getattr(member, "gamertag", "") or "").strip()
                or "Recruit"
            ),
            CharacterName=str(getattr(member, "character_name", "") or "").strip(),
            PrimaryRole=str(getattr(member, "role", "") or "").strip(),
            EsoClass=str(getattr(member, "eso_class", "") or "").strip(),
        )
        for member in getattr(plan, "members", ()) or ()
        if any(
            (
                str(getattr(member, "gamertag", "") or "").strip(),
                str(getattr(member, "character_name", "") or "").strip(),
                str(getattr(member, "eso_class", "") or "").strip(),
                tuple(getattr(member, "planned_gear_sets", ()) or ()),
                str(getattr(member, "selected_build_name", "") or "").strip(),
            )
        )
    )

    from services.comp_plan_state_service import CompPlanStateService

    comp._comp_plan_state = CompPlanStateService.from_raid_plan(
        plan,
        achievement_goal=str(comp.goal_combo.currentText() or "").strip() or None,
    )
    comp._raid_plan_origin_snapshot = plan

    comp._raid_plan_origin_id = str(getattr(plan, "plan_id", "") or "").strip()
    comp._raid_plan_origin_trial_id = str(getattr(plan, "trial_id", "") or "").strip()
    comp._raid_plan_origin_name = str(getattr(plan, "name", "") or "").strip()
    comp._raid_plan_origin_team_name = str(getattr(plan, "team_name", "") or "").strip()

    # Raid Plan owns explicit per-chair class requirements, including Recruit chairs.
    # Replace stale Comp-session state BEFORE roster intake renders anything, otherwise
    # the final Phase 14 shell can briefly reapply the previous Raid Plan's class map.
    class_by_seat = {
        next(
            (
                seat
                for seat in canonical_seats
                if "-".join(seat.casefold().split())
                == str(getattr(member, "seat_id", "") or "").strip().casefold()
            ),
            str(getattr(member, "seat_id", "") or "").strip(),
        ): str(getattr(member, "eso_class", "") or "").strip()
        for member in getattr(plan, "members", ()) or ()
        if str(getattr(member, "eso_class", "") or "").strip()
    }
    # The manual Comp picker owns ordinary five-piece overrides only. Do not seed
    # monster/mythic/arena sets into its two slots or truncate a full Raid Plan package.
    from services.comp_builder_build_candidates import _five_piece_set_names
    from engine.config import get_data_dir

    planned_sets_by_seat = {}
    for member in getattr(plan, "members", ()) or ():
        planned = tuple(
            str(value).strip()
            for value in (getattr(member, "planned_gear_sets", ()) or ())
            if str(value).strip()
        )
        if not planned:
            continue
        seat_name = next(
            (
                seat
                for seat in canonical_seats
                if "-".join(seat.casefold().split())
                == str(getattr(member, "seat_id", "") or "").strip().casefold()
            ),
            str(getattr(member, "seat_id", "") or "").strip(),
        )
        five_piece = _five_piece_set_names(get_data_dir() / "eso.db", planned)
        if five_piece:
            planned_sets_by_seat[seat_name] = tuple(five_piece[:2])

    comp._raid_plan_class_by_seat = dict(class_by_seat)
    comp._comp_class_constraint_by_slot = dict(class_by_seat)
    comp._comp_manual_gear_sets_by_slot = dict(planned_sets_by_seat)

    from ui.comp_builder_page import CompBuilderPage

    comp._comp_loading_plan = True
    try:
        comp.apply_roster_team_context(
            str(getattr(plan, "name", "") or trial_name or "Raid Plan"),
            members,
            group_size=CompBuilderPage._raid_plan_group_size(plan),
        )
    finally:
        comp._comp_loading_plan = False

    from ui.comp_builder_roster_intake_support import apply_raid_plan_class_constraints
    apply_raid_plan_class_constraints(comp, class_by_seat)
    comp._comp_manual_gear_sets_by_slot = dict(planned_sets_by_seat)

    # Final authoritative handoff: copy the current Raid Plan chair class directly
    # into the matching Comp Maker class selector after all roster/template rebuilds.
    # This deliberately bypasses Personnel/character identity. Raid Plan owns this
    # per-run chair choice, including Recruit chairs.
    from PySide6.QtWidgets import QComboBox
    for comp_row in range(comp.matrix_table.rowCount()):
        slot_name = str(comp._cell_text(comp_row, 0) or "").strip()
        wanted_class = str(class_by_seat.get(slot_name, "") or "").strip()
        if not wanted_class:
            continue
        selector = comp.matrix_table.cellWidget(comp_row, 2)
        if not isinstance(selector, QComboBox):
            continue
        match = next(
            (
                index
                for index in range(selector.count())
                if str(selector.itemText(index) or "").strip().casefold()
                == wanted_class.casefold()
            ),
            -1,
        )
        if match >= 0:
            selector.setCurrentIndex(match)

    # The backend chair selectors now contain the new Raid Plan values. Refresh the
    # visible Phase 14 projection immediately so it cannot continue showing the
    # previous Comp session's class labels.
    comp._comp_plan_state = comp._comp_plan_state.mark_saved()
    comp._comp_unbound_baseline_state = None
    try:
        from ui.comp_builder_phase14_shell_support import refresh_phase14_presentation
        refresh_phase14_presentation(comp)
    except (AttributeError, TypeError, ValueError):
        pass
    return True


def _open_plan_comp_builder(window, source_page) -> None:
    """Load the verified saved Raid Plan into Comp Builder before navigation."""
    if not _bind_plan_comp_builder(window, source_page):
        return
    window.show_page("comp_builder")


def _route_plan_page(window, source_page, target: str) -> None:
    """Preserve the current saved Raid Plan across plan-workflow navigation."""
    target = str(target or "").strip()

    if target == "comp_builder":
        _open_plan_comp_builder(window, source_page)
        return

    if target == "console:7":
        try:
            has_pending = getattr(source_page, "has_pending_changes", None)
            if callable(has_pending) and has_pending():
                status = getattr(source_page, "status", None)
                if status is not None:
                    status.warning(
                        "Save or discard Raid Plan changes before opening Coverage."
                    )
                return
            plan = getattr(source_page, "_loaded_plan_snapshot", None)
            repository = getattr(source_page, "plan_repository", None)
            if plan is not None and repository is not None:
                verified_plan = repository.get(plan.plan_id)
                plan = verified_plan if verified_plan == plan else None
        except (AttributeError, OSError, TypeError, ValueError):
            plan = None
        if plan is not None:
            _open_raid_plan_coverage(window, plan)
            return
        status = getattr(source_page, "status", None)
        if status is not None:
            status.warning(
                "Reload the saved Raid Plan before opening Coverage; the current page does not match its saved checkpoint."
            )
        return

    window.show_page(target)


def _open_finch_collaboration_workspace(
    window,
    route: str,
    context_key: str,
) -> None:
    """Open the owning workspace and restore exact local context when provenance has one."""
    route = str(route or "").strip()
    context_key = str(context_key or "").strip()
    if not route:
        return

    if route == "raid_plans" and context_key:
        page = window.pages.get("raid_plans")
        loader = getattr(page, "load_plan_by_id", None)
        if callable(loader) and loader(context_key):
            window.show_page(route)
            return

    if route == "readiness" and context_key:
        page = window.pages.get("readiness")
        if page is not None:
            refresh = getattr(page, "refresh_plans", None)
            if callable(refresh):
                refresh()
            combo = getattr(page, "plan_combo", None)
            if combo is not None:
                index = combo.findData(context_key)
                if index >= 0:
                    combo.setCurrentIndex(index)
            window.show_page(route)
            return

    if route == "console:7" and context_key:
        coverage = window.pages.get("console:7")
        raid_plans = window.pages.get("raid_plans")
        repository = getattr(raid_plans, "plan_repository", None)
        plan = repository.get(context_key) if repository is not None else None
        setter = getattr(coverage, "set_raid_plan_scope", None)
        if plan is not None and callable(setter):
            setter(plan)
            window.show_page(route)
            return

    window.show_page(route)


def _open_exact_build(window, build_id: str) -> None:
    build_id = str(build_id or "").strip()
    if not build_id:
        return
    window.show_page("console:2")
    builds = window.pages.get("console:2")
    if builds is None:
        return
    opener = getattr(builds, "show_build_by_id", None)
    if callable(opener):
        opener(build_id)


def _open_live_raid_boss_mechanics(window, encounter_id: str) -> None:
    mechanics = window.pages.get("console:4")
    if mechanics is None:
        return

    # Let normal page refresh happen first, then pin the exact Live Raid boss.
    # Otherwise Mechanics.refresh_context() can legitimately replace our selection.
    window.show_page("console:4")
    opener = getattr(mechanics, "open_encounter_by_id", None)
    if not callable(opener) or not opener(encounter_id):
        live = window.pages.get("live_raid")
        status = getattr(live, "status", None)
        if status is not None:
            status.warning("Boss Mechanics could not open the selected encounter.")
        return

    return_button = getattr(mechanics, "back_to_live_raid_button", None)
    if return_button is not None:
        try:
            return_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        return_button.clicked.connect(lambda *_: _return_to_live_raid(window))
    setter = getattr(mechanics, "set_live_raid_return_visible", None)
    if callable(setter):
        setter(True)


def _hide_live_return_for_sidebar_mechanics(window, route: str) -> None:
    if str(route or "").strip() != "console:4":
        return
    mechanics = window.pages.get("console:4")
    setter = getattr(mechanics, "set_live_raid_return_visible", None)
    if callable(setter):
        setter(False)


def _return_to_live_raid(window) -> None:
    mechanics = window.pages.get("console:4")
    if mechanics is not None:
        setter = getattr(mechanics, "set_live_raid_return_visible", None)
        if callable(setter):
            setter(False)
    window.show_page("live_raid")


def _open_live_raid_map(window, encounter_id: str, map_id: str) -> None:
    encounter_id = str(encounter_id or "").strip()
    map_id = str(map_id or "").strip()
    if not encounter_id or not map_id:
        return
    window.show_page("console:4")
    mechanics = window.pages.get("console:4")
    if mechanics is None:
        return
    opener = getattr(mechanics, "open_exact_raid_map", None)
    if callable(opener):
        opener(encounter_id, map_id)


def _register_page(window, route: str, page) -> None:
    window.pages[route] = page
    container = window.wrap_page(page)
    window.page_containers[route] = container
    window.stack.addWidget(container)


def _register_roster_workspace_refresh(window, page) -> None:
    """Reload canonical roster/build state whenever the visible Roster is opened."""

    def prepare_roster(route: str) -> None:
        if route != "roster_workspace":
            return
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()
        refresh_assets = getattr(page, "refresh_theme_assets", None)
        if callable(refresh_assets):
            refresh_assets()

    window.sidebar.pageRequested.connect(prepare_roster)


def register_raid_engine_pages(window) -> None:
    """Register the complete Urban Wilderness RAID workflow after source engine pages exist."""
    from ui.city_live_raid_page import CityLiveRaidPage
    from ui.city_raid_assignments_page import CityRaidAssignmentsPage
    from ui.city_raid_plan_workspace_page import CityRaidPlanWorkspacePage
    from ui.city_raid_readiness_page import CityRaidReadinessPage
    from ui.finch_collaboration_page import FinchCollaborationPage
    from ui.city_raid_roster_workspace_page import CityRaidRosterWorkspacePage
    from ui.raid_engine_dashboard_page import RaidEngineDashboardPage
    from ui.roster_top_back_control_support import install_roster_top_back_control

    roster_workspace = CityRaidRosterWorkspacePage()
    install_roster_top_back_control(roster_workspace)
    _register_page(window, "roster_workspace", roster_workspace)
    _register_roster_workspace_refresh(window, roster_workspace)

    assignments = CityRaidAssignmentsPage()
    assignments.pageRequested.connect(
        lambda target: _route_plan_page(window, assignments, target)
    )
    _register_page(window, "assignments", assignments)

    readiness = CityRaidReadinessPage()
    readiness.pageRequested.connect(window.show_page)
    readiness.buildRequested.connect(lambda build_id: _open_exact_build(window, build_id))
    _register_page(window, "readiness", readiness)

    finch_collaboration = FinchCollaborationPage()
    finch_collaboration.pageRequested.connect(window.show_page)
    finch_collaboration.workspaceRequested.connect(
        lambda route, context_key: _open_finch_collaboration_workspace(
            window,
            route,
            context_key,
        )
    )
    _register_page(window, "finch_collaboration", finch_collaboration)

    window.sidebar.pageRequested.connect(
        lambda route: _hide_live_return_for_sidebar_mechanics(window, route)
    )

    live_raid = CityLiveRaidPage()
    live_raid.pageRequested.connect(window.show_page)
    live_raid.bossMechanicsRequested.connect(
        lambda encounter_id: _open_live_raid_boss_mechanics(
            window,
            encounter_id,
        )
    )
    live_raid.raidMapRequested.connect(
        lambda encounter_id, map_id: _open_live_raid_map(
            window,
            encounter_id,
            map_id,
        )
    )
    _register_page(window, "live_raid", live_raid)

    dashboard = RaidEngineDashboardPage()
    dashboard.set_sources(
        comp_builder=window.pages.get("comp_builder"),
        optimization=window.pages.get("console:6"),
        coverage=window.pages.get("console:7"),
        encounters=window.pages.get("console:1"),
        performance=window.pages.get("console:3"),
    )
    dashboard.pageRequested.connect(window.show_page)
    dashboard.sendTeamRequested.connect(window._send_optimized_team_to_roster)
    dashboard.helpRequested.connect(lambda: _open_dashboard_help(window))
    _register_page(window, "raid_engine_dashboard", dashboard)

    raid_plans = CityRaidPlanWorkspacePage()
    raid_plans.pageRequested.connect(
        lambda target: _route_plan_page(window, raid_plans, target)
    )
    raid_plans.assignmentsRequested.connect(
        lambda plan_id: _open_saved_plan_assignments(window, plan_id)
    )
    raid_plans.raidMapRequested.connect(lambda plan_id: _open_raid_plan_map(window, plan_id))
    raid_plans.coverageRequested.connect(lambda plan: _open_raid_plan_coverage(window, plan))
    raid_plans.rotationRequested.connect(
        lambda plan, seat_id: _open_raid_plan_rotation(window, plan, seat_id)
    )
    raid_plans.adviserRequested.connect(lambda plan: _open_raid_plan_adviser(window, plan))
    _register_page(window, "raid_plans", raid_plans)

    # Roster is the application landing surface for the streamlined workspace.
    # Keep the legacy roster route registered for old handoffs, but do not make
    # people navigate through it merely because software enjoys archaeology.
    window.show_page("roster_workspace")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.build_screenshot_import_disable_support import (
        install as install_build_screenshot_import_disable_support,
    )
    from ui.coverage_raid_plan_scope_support import install as install_coverage_raid_plan_scope_support
    from ui.team_optimization_phase14_shell_support import (
        install as install_team_optimization_phase14_shell_support,
    )

    install_coverage_raid_plan_scope_support()
    # Phase 14 owns the exact RaidPlan handoff directly. The legacy adviser adapter
    # remains compatibility code but is no longer imported/constructed at startup.
    install_team_optimization_phase14_shell_support()
    _install_canonical_sidebar_routes()
    from ui.raid_engine_dashboard_polish_support import install as install_dashboard_polish
    install_dashboard_polish()
    _install_safe_dashboard_rewire()
    install_build_screenshot_import_disable_support()
    _INSTALLED = True
