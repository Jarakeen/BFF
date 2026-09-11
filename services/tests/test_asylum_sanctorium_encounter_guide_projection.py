from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _markers(projection):
    return {row.marker for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_asylum_olms_projection_preserves_plus_mode_join_thresholds_and_priority_calls():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "saint_olms_encounter", "Saint Olms the Just"
    )

    assert {"Olms Base Fight", "Llothis Joins", "Felms Joins"} <= _labels(projection)
    assert {"Pull", "90-91%", "75-76%"} <= _markers(projection)

    strategy = _strategy(projection)
    assert "Protectors" in strategy
    assert "first priority" in strategy["Protectors"].mitigation.casefold()
    assert "Side Saint Enrage" in strategy
    assert "3-minute enrage" in strategy["Side Saint Enrage"].mitigation
    assert "45 seconds" in strategy["Side Saint Enrage"].mitigation
    assert "Llothis Interrupt" in strategy
    assert "interrupt" in strategy["Llothis Interrupt"].mitigation.casefold()
    assert "Steam Breath" in strategy
    assert "facing away from the raid" in strategy["Steam Breath"].mitigation
