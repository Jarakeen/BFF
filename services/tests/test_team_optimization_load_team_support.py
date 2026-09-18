from pathlib import Path


def test_optimization_replaces_team_source_with_load_team() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert 'page._context_field("LOAD TEAM", page.load_team_combo)' in source
    assert 'page.load_team_combo.addItem("Select team…", "")' in source
    assert "_all_named_teams(page)" in source
    assert "_hide_team_source(page)" in source


def test_optimization_uses_generated_roster_draft_api_not_legacy_plan_aliases() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "GeneratedRosterDraftService" in source
    assert "GeneratedRosterDraftSlot" in source
    assert "GeneratedRosterPlanService" not in source
    assert "GeneratedRosterPlanSlot" not in source


def test_load_team_prefers_exact_generated_plan_before_roster_autofill() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    generated_lookup = source.index("page._optimization_generated_plan_service.load_plan(team)")
    roster_members = source.index("page._optimization_roster_service.list_members()")
    assert generated_lookup < roster_members
    assert "_load_generated_team_plan(page, generated)" in source
    assert "without reranking its chairs" in source


def test_load_team_targets_active_compare_editor_and_remembers_identity() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "page.team_tabs.currentIndex() == 1" in source
    assert "return page.team_b_table" in source
    assert "return page.team_table" in source
    assert '"_optimization_loaded_team_name_b"' in source
    assert '"_optimization_loaded_team_name_a"' in source
    assert '"_optimization_loaded_generated_plan_b"' in source
    assert '"_optimization_loaded_generated_plan_a"' in source
    assert "_remember_loaded_team(page, table, plan.name, plan)" in source


def test_roster_only_team_fallback_still_consumes_each_player_once() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "build_role_compatible_autofill(" in source
    assert "build_player_keys=tuple(" in source
    assert "global_index = eligible_indices[assignment.build_index]" in source
    assert "team.casefold() in _team_names_for_member(member)" in source


def test_optimization_preserves_loaded_team_identity_when_sending_to_raid_plan() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "team_name = _loaded_team_name(optimization_page)" in source
    assert "base_plan.team_name if base_plan is not None else" in source
    assert 'else team_name or f"{goal} Optimized Team"' in source
    assert "team_name=team_name or None" in source
    assert "base_plan=base_plan" in source
    assert 'f"Sent {plan.name!r} to Raid Plan' in source
    assert 'f"Optimizer changes loaded into Raid Plan: {plan.name}."' in source
    assert '"required_slot_combo", "required_class_combo", "required_gear_input"' in source


def test_optimization_round_trip_preserves_unchanged_structured_assignment_evidence() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(encoding="utf-8")

    assert "def _original_slot_by_name" in source
    assert "def _slot_from_optimization_row" in source
    assert "source_kind=original.source_kind" in source
    assert "source_name=original.source_name" in source
    assert "source_url=original.source_url" in source
    assert "candidate_id=original.candidate_id" in source
    assert "gear_sets=original.gear_sets" in source
    assert "skills=original.skills" in source
    assert "mundus=original.mundus" in source
    assert "elif not is_saved and original.kind != \"saved\"" in source


def test_final_optimizer_send_handler_targets_raid_plan_not_roster() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(
        encoding="utf-8"
    )

    handler = source.split(
        "def _send_visible_optimization_team_to_raid_plan", 1
    )[1].split("def install()", 1)[0]

    assert "raid_plan_from_generated_slots" in handler
    assert 'window.pages.get("raid_plans")' in handler
    assert "raid_plans.plan_repository.save(plan)" in handler
    assert "raid_plans.apply_plan(plan)" in handler
    assert 'window.show_page("raid_plans")' in handler
    assert 'window.show_page("roster_page")' not in handler
    assert "base_plan=base_plan" in handler


def test_final_optimizer_override_installs_raid_plan_sender() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(
        encoding="utf-8"
    )

    assert (
        "MainWindow._send_optimized_team_to_roster = "
        "_send_visible_optimization_team_to_raid_plan"
    ) in source


def test_visible_optimizer_slot_carries_saved_build_evidence() -> None:
    source = Path("ui/team_optimization_role_cleanup.py").read_text(
        encoding="utf-8"
    )

    assert "build_gear_set_names(build)" in source
    assert "skills = _build_skills(build)" in source
    assert 'getattr(build, "Mundus", "")' in source
    assert 'source_kind="optimizer_visible_team"' in source
    assert 'candidate_id=f"optimizer-visible:{slot_name}"' in source
