from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _markers(projection):
    return {row.marker for row in projection.timeline}


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_cloudrest_minibosses_project_signature_mechanics():
    relequen = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("relequen", "Relequen")
    galenwe = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("galenwe", "Galenwe")
    siroria = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("siroria", "Siroria")

    relequen_strategy = _strategy(relequen)
    assert "Voltaic Overload" in relequen_strategy
    assert "Swap bars" in relequen_strategy["Voltaic Overload"].mitigation
    assert "Lightning Channel" in relequen_strategy
    assert "Interrupt" in relequen_strategy["Lightning Channel"].mitigation

    galenwe_strategy = _strategy(galenwe)
    assert "Hoarfrost" in galenwe_strategy
    assert "drop synergy" in galenwe_strategy["Hoarfrost"].mitigation
    assert "Ice Comet" in galenwe_strategy
    assert "three targets" in galenwe_strategy["Ice Comet"].mitigation.lower()

    assert "~50%" in _markers(siroria)
    siroria_strategy = _strategy(siroria)
    assert "Roaring Flare" in siroria_strategy
    assert "Stack" in siroria_strategy["Roaring Flare"].mitigation


def test_zmaja_projection_preserves_plus_one_two_three_spawn_structure():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("z_maja", "Z'Maja")

    assert {"Pull", "65%", "50%", "35%", "75%", "25%"} <= _markers(projection)
    labels = _labels(projection)
    assert {"+1 Shade Spawn", "+2 First Shade Spawn", "+2 Second Shade Spawn", "+3 Siroria Spawn", "+3 Relequen Spawn", "+3 Galenwe Spawn"} <= labels

    strategy = _strategy(projection)
    assert "Shade Mechanics Persist" in strategy
    assert "+1/+2/+3" in strategy["Shade Mechanics Persist"].mitigation
    assert "Teleport / Facing" in strategy
    assert "faced away" in strategy["Teleport / Facing"].mitigation
