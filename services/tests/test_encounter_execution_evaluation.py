from pathlib import Path

from minmax.coverage_classification import CoverageClassification
from services.encounter_execution_evaluation import EncounterExecutionEvaluator
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def _evaluator() -> EncounterExecutionEvaluator:
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    return EncounterExecutionEvaluator(service)


def test_oaxiltso_cleanse_is_build_independent_but_movement_and_positioning_stay_unknown():
    result = _evaluator().evaluate("oaxiltso")

    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")
    movement = next(row for row in result.results if row.requirement_type == "movement")
    positioning = next(row for row in result.results if row.requirement_type == "positioning")

    assert cleanse.classification == CoverageClassification.COVERED
    assert cleanse.handling_method == "encounter_interaction"
    assert cleanse.interaction == "cleanse_pool"
    assert cleanse.requires_player_build_capability is False
    assert movement.classification == CoverageClassification.UNKNOWN
    assert positioning.classification == CoverageClassification.UNKNOWN
    assert result.is_fully_evaluable is False
    assert result.is_fully_ready is False


def test_hiath_break_free_and_standard_interrupts_are_build_independent_capabilities():
    result = _evaluator().evaluate("hiath_the_battlemaster")

    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")
    interrupts = tuple(row for row in result.results if row.requirement_type == "interrupt")

    assert cleanse.classification == CoverageClassification.COVERED
    assert cleanse.handling_method == "core_action"
    assert cleanse.interaction == "break_free"
    assert cleanse.requires_player_build_capability is False
    assert len(interrupts) == 3
    assert all(row.classification == CoverageClassification.COVERED for row in interrupts)
    assert all(row.handling_method == "core_bash" for row in interrupts)
    assert all(row.requires_player_build_capability is False for row in interrupts)


def test_xalvakka_soul_purge_synergy_is_ready_without_inventing_purge_skill_requirement():
    result = _evaluator().evaluate("xalvakka")

    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.COVERED
    assert cleanse.handling_method == "encounter_interaction"
    assert cleanse.interaction == "soul_purge_synergy"
    assert cleanse.requires_player_build_capability is False


def test_real_standard_interrupt_requirement_is_covered_by_global_core_action_rule():
    result = _evaluator().evaluate("achelir")
    interrupt = next(row for row in result.results if row.requirement_type == "interrupt")

    assert interrupt.classification == CoverageClassification.COVERED
    assert interrupt.handling_method == "core_bash"
    assert interrupt.requires_player_build_capability is False
    assert "not successful player execution" in interrupt.explanation
