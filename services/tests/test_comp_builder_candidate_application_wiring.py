from pathlib import Path


def test_comp_maker_can_apply_top_ranked_candidate_to_selected_chair():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert '"Apply Top Candidate"' in source
    assert "_first_unused_candidate(candidates, used_saved_players)" in source
    assert "page._comp_applied_candidates[slot_name] = candidate" in source
    assert "Applied {candidate.name} to {slot_name}" in source


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


def test_fill_from_roster_uses_saved_build_candidates_only():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert 'if candidate.source_kind == "saved_build"' in source
    assert "Reference templates remain" in source
    assert "Filled {result.applied_count} open chair(s) from saved roster builds" in source
    assert "no matching saved roster build" in source


def test_comp_maker_send_to_roster_preserves_structured_candidate_evidence():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "GeneratedRosterPlanSlot(" in source
    assert 'kind="saved" if is_saved else "prescribed_recruit"' in source
    assert "build_name=candidate.name" in source
    assert 'gear_summary=" + ".join(candidate.gear_sets)' in source
    assert "role=candidate.role or role" in source
    assert "source_kind=candidate.source_kind" in source
    assert "source_name=candidate.source_name" in source
    assert "source_url=candidate.source_url" in source
    assert "candidate_id=candidate.candidate_id" in source
    assert "gear_sets=tuple(candidate.gear_sets)" in source
    assert "skills=tuple(candidate.skills)" in source
    assert "mundus=candidate.mundus" in source
    assert "Observed/known skills:" not in source


def test_comp_maker_does_not_turn_reference_templates_into_fake_players():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert 'player_name=candidate.source_name if is_saved else "Recruitment Needed"' in source
    assert 'character_name=candidate.source_name if is_saved else ""' in source
    assert "Candidate is partial evidence, not a complete prescribed build." in source


def test_comp_maker_bulk_optimizer_enforces_raid_wide_provider_coverage():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert "required_team_provider_ids: list[str] = []" in source
    assert "required_team_provider_ids.extend(provider_resolution.provider_ids)" in source
    assert "required_team_provider_ids = list(dict.fromkeys(required_team_provider_ids))" in source
    assert "already_covered_team_provider_ids.update(" in source
    assert "required_team_provider_ids=tuple(required_team_provider_ids)" in source
    assert "already_covered_team_provider_ids=tuple(sorted(already_covered_team_provider_ids))" in source
    assert "raid-wide provider still uncovered" in source


def test_comp_maker_raid_wide_provider_scope_comes_from_active_template_rows():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert "provider_labels = page._split_values(page._cell_text(row, 6))" in source
    assert "provider_resolution_by_slot[slot_name] = provider_resolution" in source
    assert "for row in provider_service.profile.mapped_required" not in source.split(
        "already_covered_team_provider_ids", 1
    )[0]


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
