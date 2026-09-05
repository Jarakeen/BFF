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


def test_comp_maker_send_to_roster_preserves_applied_candidate_build_evidence():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "GeneratedRosterPlanSlot(" in source
    assert 'kind="prescribed_player" if is_saved else "prescribed_recruit"' in source
    assert "build_name=candidate.name" in source
    assert 'gear_summary=" + ".join(candidate.gear_sets)' in source
    assert "_candidate_unresolved(candidate, detail)" in source


def test_comp_maker_does_not_turn_reference_templates_into_fake_players():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert 'player_name=candidate.source_name if is_saved else "Recruitment Needed"' in source
    assert 'character_name=candidate.source_name if is_saved else ""' in source
    assert "Candidate is partial evidence, not a complete prescribed build." in source


def test_comp_maker_bulk_optimizer_enforces_raid_wide_provider_coverage():
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(encoding="utf-8")

    assert "required_team_provider_ids = tuple(" in source
    assert "already_covered_team_provider_ids.update(" in source
    assert "required_team_provider_ids=required_team_provider_ids" in source
    assert "already_covered_team_provider_ids=tuple(sorted(already_covered_team_provider_ids))" in source
    assert "raid-wide provider still uncovered" in source
