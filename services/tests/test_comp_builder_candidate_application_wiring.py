from pathlib import Path


def test_comp_maker_can_apply_top_ranked_candidate_to_selected_chair():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert '"Apply Top Candidate"' in source
    assert "_first_unused_candidate(candidates, used_saved_players)" in source
    assert "page._comp_applied_candidates[slot_name] = candidate" in source
    assert "Applied unlocked parts of {candidate.name} to {slot_name}" in source
    assert "_comp_last_candidate_apply_changed" in source
    assert "_comp_last_candidate_apply_blocked_fields" in source


def test_comp_maker_can_apply_best_candidates_across_unassigned_chairs():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert '"Apply Best to All Chairs"' in source
    assert "def _apply_best_candidates_to_all" in source
    assert "if slot_name in page._comp_applied_candidates" in source
    assert "skipped_existing += 1" in source
    assert "_set_candidate_for_row(page, row, candidate)" in source


def test_comp_maker_bulk_application_does_not_clone_saved_players():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "def _saved_player_key" in source
    assert "def _first_unused_candidate" in source
    assert "if player_key and player_key in used_saved_players" in source
    assert "used_saved_players.add(player_key)" in source


def test_canonical_autofill_can_consider_saved_and_reference_build_evidence():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert 'candidate.source_kind in {"saved_build", "reference_template"}' in source
    assert "CompPlanAutoFillService" in source
    assert "Filled {result.applied_count} open roster/build decision(s)" in source
    assert "Compatibility mirror only" in source


def test_phase14_candidate_support_does_not_restore_retired_generated_roster_writer():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "GeneratedRosterDraftSlot(" not in source
    assert "GeneratedRosterPlanSlot" not in source
    assert "def _send_to_roster_with_candidates" not in source
    assert "save_generated_plan" not in source
    assert "_comp_plan_state" in source
    assert "planned_gear_sets" in source


def test_reference_candidates_remain_planning_evidence_without_player_identity_writes():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    changes = source.split("def _candidate_state_changes", 1)[1].split(
        "def _refresh_candidates", 1
    )[0]
    assert 'candidate.source_kind == "saved_build"' in changes
    assert 'changes["selected_build_id"]' in changes
    assert 'changes["selected_build_name"]' in changes
    assert "player_name" not in changes
    assert "character_name" not in changes
    assert "planned_gear_sets" in changes


def test_comp_maker_autofill_uses_assignments_as_provider_constraints() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )

    assert "CompBuilderProviderEvidenceService" in source
    assert "chair.primary_assignment" in source
    assert "chair.secondary_assignment" in source
    assert "required_by_seat[chair.seat_id] = tuple(dict.fromkeys(provider_ids))" in source
    assert "required_provider_ids=tuple(local_required)" in source
    assert "provider_ids_by_candidate=provider_ids_by_candidate" in source
    assert "health.missing_required" not in source
    assert "CompPlanHealthService" not in source
    assert "provider_sources_for_candidate" in source
    assert "assignment_source" in source


def test_comp_maker_team_health_reports_coverage_without_assigning_jobs() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )
    health = Path("ui/comp_builder_phase14_shell_support.py").read_text(
        encoding="utf-8"
    )

    assert "Assignments owns WHO. Comp Maker owns HOW." in source
    assert "_cached_comp_health(page, state)" in health
    assert "CompPlanHealthService" in health
    assert "health.missing_required" not in source


def test_phase14_comp_send_quarantines_generated_draft_writer() -> None:
    shell = Path("ui/comp_builder_phase14_shell_support.py").read_text(
        encoding="utf-8"
    )
    bootstrap = Path("ui/application_team_optimization_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "def _send_to_raid_plan_method(self, *_args) -> None:" in shell
    assert "CompBuilderPage._send_to_roster = _send_to_raid_plan_method" in shell
    assert "install_comp_builder_authoritative_prescription()" not in bootstrap
    assert "comp_builder_authoritative_prescription_support" not in bootstrap
    candidates = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")
    constraints = Path("ui/comp_builder_build_constraint_support.py").read_text(encoding="utf-8")
    feedback = Path("ui/comp_builder_send_feedback_support.py").read_text(encoding="utf-8")
    assert "CompBuilderPage._send_to_roster = _send_to_roster_with_candidates" not in candidates
    assert "CompBuilderPage._send_to_roster = _send_to_roster_with_constraint_validation" not in constraints
    assert "CompBuilderPage._send_to_roster = _send_to_roster_with_feedback" not in feedback


def test_candidate_application_writes_effective_gear_to_canonical_plan_state():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    changes = source.split("def _candidate_state_changes", 1)[1].split(
        "def _refresh_candidates", 1
    )[0]
    assert 'changes["planned_gear_sets"] = tuple(candidate.gear_sets)' in changes
    assert "chair.is_locked(\"gear\")" in changes
    assert "_replace_state_chair(page, chair.with_changes(**changes))" in source


def test_candidate_helpers_use_canonical_state_before_compatibility_mirror() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    used = source.split("def _used_saved_players(page)", 1)[1].split(
        "def _format_candidates", 1
    )[0]
    assert 'state = getattr(page, "_comp_plan_state", None)' in used
    assert "chair.build_source_kind" in used
    assert "chair.player_id" in used
    assert "chair.character_id" in used
    assert "chair.selected_build_id" in used
    assert "chair.build_source_name" not in used
    assert "return canonical | mirror" in used

    formatted = source.split("def _format_candidates(page)", 1)[1].split(
        "def _state_chair_for_row", 1
    )[0]
    assert "chair = _state_chair_for_row(page, row)" in formatted
    assert "chair.candidate_id" in formatted
    assert "candidate.candidate_id == chair.candidate_id" in formatted


def test_candidate_apply_has_no_state_less_write_path() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")
    apply = source.split("def _set_candidate_for_row", 1)[1].split(
        "def _apply_top_candidate", 1
    )[0]

    assert 'if chair is None:' in apply
    assert "requires canonical Comp planning state" in apply
    assert 'changes = {"legacy": True}' not in apply
