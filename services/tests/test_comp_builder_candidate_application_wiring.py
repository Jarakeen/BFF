from pathlib import Path


def test_comp_maker_can_apply_top_ranked_candidate_to_selected_chair():
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert '"Apply Top Candidate"' in source
    assert "candidate = candidates[0]" in source
    assert "page._comp_applied_candidates[slot_name] = candidate" in source
    assert "Applied {candidate.name} to {slot_name}" in source


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
