from pathlib import Path

from minmax.coverage_classification import CoverageClassification
from services.encounter_execution_difficulty import DifficultyAwareEncounterExecutionEvaluator
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def _evaluator() -> DifficultyAwareEncounterExecutionEvaluator:
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    return DifficultyAwareEncounterExecutionEvaluator(service)


def test_oaxiltso_veteran_keeps_source_backed_cleanse_pool_ready():
    result = _evaluator().evaluate("oaxiltso", "veteran")
    sludge = {
        row.requirement_type: row
        for row in result.results
        if row.mechanic_name == "Noxious Sludge"
    }

    assert sludge["movement"].classification == CoverageClassification.COVERED
    assert sludge["movement"].interaction == "cleanse_pool"
    assert sludge["cleanse"].classification == CoverageClassification.COVERED
    assert sludge["cleanse"].interaction == "cleanse_pool"
    assert result.is_fully_ready is True


def test_oaxiltso_hardmode_disables_only_cleanse_pool_dependent_rows():
    result = _evaluator().evaluate("oaxiltso", "hardmode")
    rows = {(row.mechanic_name, row.requirement_type): row for row in result.results}

    for key in (
        ("Noxious Sludge", "movement"),
        ("Noxious Sludge", "cleanse"),
    ):
        row = rows[key]
        assert row.classification == CoverageClassification.UNKNOWN
        assert row.interaction == "cleanse_pool"
        assert "disables the cleanse pools" in row.explanation

    assert rows[("Noxious Sludge", "positioning")].classification == CoverageClassification.COVERED
    assert rows[("Savage Blitz", "movement")].classification == CoverageClassification.COVERED
    assert rows[("Savage Blitz", "positioning")].classification == CoverageClassification.COVERED
    assert rows[("Blistering Smash", "positioning")].classification == CoverageClassification.COVERED
    assert rows[("Summon Havocrel Annihilators", "positioning")].classification == CoverageClassification.COVERED
    assert len(result.unknown) == 2
    assert result.is_fully_evaluable is False
    assert result.is_fully_ready is False


def test_oaxiltso_hm_alias_normalizes_to_hardmode():
    result = _evaluator().evaluate("oaxiltso", "hm")
    assert len(result.unknown) == 2
