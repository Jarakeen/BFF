from pathlib import Path

from minmax.coverage_classification import CoverageClassification
from services.encounter_cleanse_method import (
    CleanseMethod,
    CleanseMethodResolution,
    EncounterCleanseMethod,
)
from services.encounter_execution_evaluation import EncounterExecutionEvaluator
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterRequirement, EncounterService


ROOT = Path(__file__).resolve().parents[2]


def _evaluator() -> EncounterExecutionEvaluator:
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    return EncounterExecutionEvaluator(service)


def _cleanse_requirement(requirement_id: str, mechanic_name: str) -> EncounterRequirement:
    return EncounterRequirement(
        requirement_id=requirement_id,
        encounter_id="fixture",
        mechanic_id=requirement_id,
        mechanic_name=mechanic_name,
        requirement_type="cleanse",
        target_count=None,
        interpretation_status="structured",
    )


def _legacy_method(fact_id: str, mechanic_name: str) -> EncounterCleanseMethod:
    return EncounterCleanseMethod(
        encounter_id="fixture",
        mechanic_name=mechanic_name,
        method=CleanseMethod.ENCOUNTER_INTERACTION,
        resolution=CleanseMethodResolution.RESOLVED,
        interaction="fixture_interaction",
        fact_id=fact_id,
        reconciliation_status="corroborated",
        distinct_sources=2,
    )


def test_oaxiltso_structured_execution_methods_are_build_independent_and_source_backed():
    result = _evaluator().evaluate("oaxiltso")
    rows = {(row.mechanic_name, row.requirement_type): row for row in result.results}

    expected = {
        ("Savage Blitz", "movement"): ("dodge", ""),
        ("Savage Blitz", "positioning"): ("bait_farthest", ""),
        ("Noxious Sludge", "movement"): ("move_to_interaction", "cleanse_pool"),
        ("Noxious Sludge", "positioning"): ("hazard_drop_management", "noxious_pool"),
        ("Noxious Sludge", "cleanse"): ("encounter_interaction", "cleanse_pool"),
        ("Summon Havocrel Annihilators", "positioning"): ("separate_add_from_boss", ""),
    }

    assert set(rows) == set(expected)
    assert not any(row.mechanic_name == "Blistering Smash" for row in result.results)
    for key, (method, interaction) in expected.items():
        row = rows[key]
        assert row.classification == CoverageClassification.COVERED
        assert row.handling_method == method
        assert row.interaction == interaction
        assert row.requires_player_build_capability is False

    assert result.is_fully_evaluable is True
    assert result.is_fully_ready is True


def test_hiath_break_free_and_reviewed_interrupts_are_build_independent_capabilities():
    result = _evaluator().evaluate("hiath_the_battlemaster")

    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")
    interrupts = tuple(row for row in result.results if row.requirement_type == "interrupt")

    assert cleanse.classification == CoverageClassification.COVERED
    assert cleanse.handling_method == "core_action"
    assert cleanse.interaction == "break_free"
    assert cleanse.requires_player_build_capability is False
    assert len(interrupts) == 2
    assert all(row.classification == CoverageClassification.COVERED for row in interrupts)
    assert all(row.handling_method == "core_bash" for row in interrupts)
    assert all(row.requires_player_build_capability is False for row in interrupts)


def test_xalvakka_rejected_raw_cleanse_does_not_reach_execution_evaluation():
    result = _evaluator().evaluate("xalvakka")

    assert not any(row.requirement_type == "cleanse" for row in result.results)


def test_real_standard_interrupt_requirement_is_covered_by_global_core_action_rule():
    result = _evaluator().evaluate("achelir")
    interrupt = next(row for row in result.results if row.requirement_type == "interrupt")

    assert interrupt.classification == CoverageClassification.COVERED
    assert interrupt.handling_method == "core_bash"
    assert interrupt.requires_player_build_capability is False
    assert "not successful player execution" in interrupt.explanation


def test_single_unmatched_cleanse_requirement_and_method_are_joined_one_to_one():
    requirement = _cleanse_requirement("cleanse-1", "Canonical Mechanic")
    legacy = _legacy_method("fact-1", "legacy_fact_key")

    joined = EncounterExecutionEvaluator._cleanse_methods_by_requirement(
        (requirement,),
        (legacy,),
    )

    assert joined == {"cleanse-1": legacy}


def test_ambiguous_unmatched_cleanse_methods_are_not_guessed():
    requirements = (
        _cleanse_requirement("cleanse-1", "Mechanic One"),
        _cleanse_requirement("cleanse-2", "Mechanic Two"),
    )
    methods = (
        _legacy_method("fact-1", "legacy_one"),
        _legacy_method("fact-2", "legacy_two"),
    )

    joined = EncounterExecutionEvaluator._cleanse_methods_by_requirement(
        requirements,
        methods,
    )

    assert joined == {}
