from __future__ import annotations

from pathlib import Path

from tools import audit_extreme_e2_actual_heal_ordinary_gear_denominator as audit


def test_denominator_row_distinguishes_positive_complete_and_unresolved_states() -> None:
    complete = audit.OrdinaryGearDenominatorRow(
        set_id=1,
        set_name="Complete Set",
        category="Dungeon",
        useful_piece_count=5,
        reviewed_positive_objectives=("healing_done",),
        unresolved_objectives=(),
        selected_by_authoritative_search=True,
        selected_by_bounded_comparison=False,
        shared_numeric_positive_objectives=("healing_done",),
    )
    specialist = audit.OrdinaryGearDenominatorRow(
        set_id=2,
        set_name="Specialist Set",
        category="Trial",
        useful_piece_count=5,
        reviewed_positive_objectives=("spell_damage",),
        unresolved_objectives=(),
        selected_by_authoritative_search=True,
        selected_by_bounded_comparison=False,
        shared_numeric_positive_objectives=(),
    )
    unresolved = audit.OrdinaryGearDenominatorRow(
        set_id=3,
        set_name="Unresolved Set",
        category="Trial",
        useful_piece_count=5,
        reviewed_positive_objectives=("max_magicka",),
        unresolved_objectives=("healing_done",),
        selected_by_authoritative_search=False,
        selected_by_bounded_comparison=False,
        shared_numeric_positive_objectives=("max_magicka",),
    )

    assert complete.reviewed_positive is True
    assert complete.mechanic_complete_for_h1_screen is True
    assert complete.specialist_only_positive is False
    assert specialist.reviewed_positive is True
    assert specialist.specialist_only_positive is True
    assert unresolved.reviewed_positive is True
    assert unresolved.mechanic_complete_for_h1_screen is False


def test_audit_source_uses_complete_repository_preload_and_all_h1_objectives() -> None:
    source = Path(audit.__file__).read_text(encoding="utf-8")

    assert "repository.preload_all_static()" in source
    assert "ExtremeActualHealGearSetCandidateService.OBJECTIVES" in source
    assert "ExtremeGearSetObjectiveService.candidate_for_set" in source
    assert "review.h1_positive_modifier_proven" in source
    assert "shared_numeric_reviewed_positive_set_count=" in source
    assert "specialist_only_reviewed_positive_set_count=" in source
    assert "selected_by_authoritative_search" in source
    assert "global_gear_family_denominator_complete=False" in source


def test_audit_separates_authoritative_exhaustive_search_from_bounded_comparison() -> None:
    source = Path(audit.__file__).read_text(encoding="utf-8")

    assert 'candidate_set_names(per_objective=None)' in source
    assert "authoritative_per_objective_candidate_cap=None" in source
    assert "comparison_per_objective_candidate_cap=" in source
    assert "authoritative_search_omitted_mechanic_complete_reviewed_positive_count=" in source
    assert "ordinary_gear_authoritative_reviewed_denominator_complete=" in source
    assert "monster sets, mythics, arena weapons, and runtime proc families" in source
