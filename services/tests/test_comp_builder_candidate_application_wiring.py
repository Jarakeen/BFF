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
    assert "Auto-filled {result.applied_count} open build decision(s)" in source
    assert "Compatibility mirror only" in source


def test_comp_maker_send_to_roster_preserves_structured_candidate_evidence():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "GeneratedRosterDraftSlot(" in source
    assert "GeneratedRosterPlanSlot" not in source
    assert 'kind="saved" if is_saved or known_player else "prescribed_recruit"' in source
    assert '"Manual gear package"' in source
    assert "_effective_candidate_gear_sets(" in source
    assert "role=candidate.role or role" in source
    assert "source_kind=candidate.source_kind" in source
    assert "source_name=candidate.source_name" in source
    assert "source_url=candidate.source_url" in source
    assert "candidate_id=candidate.candidate_id" in source
    assert "gear_sets=effective_gear_sets" in source
    assert "skills=tuple(candidate.skills)" in source
    assert "mundus=candidate.mundus" in source
    assert "Observed/known skills:" not in source


def test_comp_maker_does_not_turn_reference_templates_into_fake_players():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    save = source.split("def save_generated_plan", 1)[1].split(
        "def _send_to_roster_with_candidates", 1
    )[0]
    assert 'roster_player if known_player else (' in save
    assert 'candidate.source_name if is_saved else "Recruitment Needed"' in save
    assert 'roster_character if known_player else (' in save
    assert 'candidate.source_name if is_saved else ""' in save
    assert 'is_saved = candidate.source_kind == "saved_build"' in save
    assert "Candidate is partial evidence, not a complete prescribed build." in source


def test_comp_maker_bulk_optimizer_enforces_raid_wide_provider_coverage():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert "required_team_provider_ids: list[str] = []" in source
    assert "required_team_provider_ids.extend(provider_resolution.provider_ids)" in source
    assert "required_team_provider_ids = list(dict.fromkeys(required_team_provider_ids))" in source
    assert "already_covered_team_provider_ids.update(" in source
    assert "required_team_provider_ids=tuple(required_team_provider_ids)" in source
    assert "already_covered_team_provider_ids=tuple(" in source
    assert "sorted(already_covered_team_provider_ids)" in source
    assert "raid-wide provider still uncovered" in source


def test_canonical_comp_provider_scope_comes_from_team_health_and_assignments():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert "CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)" in source
    assert source.count("CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)") == 1
    assert "health.missing_required" in source
    assert "chair.primary_assignment" in source
    assert "provider_resolution_by_slot[chair.seat_id]" in source
    assert "assignment_resolution.provider_ids" in source
    assert "provider_labels = page._split_values(page._cell_text(row, 6))" not in source
    assert "Canonical bound and unbound sessions" in source


def test_comp_maker_materializes_optimizer_choices_before_roster_transfer():
    source = Path("ui/comp_builder_authoritative_prescription_support.py").read_text(
        encoding="utf-8"
    )

    assert "CompBuilderAuthoritativePrescriptionService" in source
    assert "candidates_by_slot=dict(applied)" in source
    assert "page._comp_current_prescription = prescription" in source
    assert "_materialize_current_comp(self)" in source
    assert "_ORIGINAL_SEND_TO_ROSTER(self)" in source

    send_function = source.split(
        "def _send_to_roster_with_authoritative_prescription", 1
    )[1].split("def install", 1)[0]
    assert send_function.index("_materialize_current_comp(self)") < send_function.index(
        "_ORIGINAL_SEND_TO_ROSTER(self)"
    )


def test_comp_maker_manual_five_piece_override_preserves_non_five_piece_candidate_gear():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert 'getattr(page, "_comp_manual_gear_sets_by_slot", {})' in source
    assert "def _effective_candidate_gear_sets(" in source
    assert "candidate.five_piece_sets" in source
    assert "preserved_non_five" in source
    assert "effective_gear_sets = _effective_candidate_gear_sets(" in source
    assert 'gear_summary=" + ".join(effective_gear_sets)' in source
    assert "gear_sets=effective_gear_sets" in source
