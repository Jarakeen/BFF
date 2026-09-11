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


def test_lightning_storm_atronach_has_safe_zone_and_shockwave_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "lightning_storm_atronach", "Lightning Storm Atronach"
    )
    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Storm Safe Zone" in strategy
    assert "lit pad" in strategy["Storm Safe Zone"].mitigation
    assert "Shockwave" in strategy
    assert "block" in strategy["Shockwave"].mitigation.casefold()


def test_foundation_stone_has_ground_pound_and_add_pair_tank_roles():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "foundation_stone_atronach", "Foundation Stone Atronach"
    )
    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Ground Pound" in strategy
    assert "five-hit" in strategy["Ground Pound"].mitigation
    assert "Add Pair" in strategy
    assert "Off-tank" in strategy["Add Pair"].mitigation


def test_varlariel_has_thirty_second_clone_cycle():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "varlariel", "Varlariel"
    )
    assert {"Main Phase", "Clone Split Cycle"} <= _labels(projection)
    assert "~30s cycle" in _markers(projection)
    strategy = _strategy(projection)
    assert "Clone Split" in strategy
    assert "three clones" in strategy["Clone Split"].mitigation


def test_mage_has_execute_chain_lightning_axes_and_hm_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "the_mage_celestial", "The Mage"
    )
    assert {"Main Phase", "Execute"} <= _labels(projection)
    assert "~15%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Chain Lightning" in strategy
    assert "spacing" in strategy["Chain Lightning"].mitigation.casefold()
    assert "Axes" in strategy
    assert "Storm Atronachs" in strategy
    assert "Hard Mode" in strategy["Storm Atronachs"].mitigation
