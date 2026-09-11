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


def test_zhaj_hassa_projection_has_cleanse_and_pillar_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "zhaj_hassa_the_forgotten", "Zhaj'hassa the Forgotten"
    )

    assert {"Main Phase", "Escalating Curse / Pillar Pressure"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Cleanse Pads" in strategy
    assert "two players per cleanse pad" in strategy["Cleanse Pads"].mitigation
    assert "Pillar Placement" in strategy
    assert "assigned position" in strategy["Pillar Placement"].mitigation


def test_twins_projection_has_split_conversion_and_tank_swap_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "s_kinrai_vashai", "S'kinrai and Vashai"
    )

    assert {"Split Groups", "Conversions"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Color Rule" in strategy
    assert "opposite-color boss" in strategy["Color Rule"].mitigation
    assert "Tank Boss Swap" in strategy
    assert "swap bosses" in strategy["Tank Boss Swap"].mitigation
    assert "Radiant Oppression" in strategy
    assert "Interrupt" in strategy["Radiant Oppression"].mitigation


def test_rakkhat_projection_has_pad_runner_lunar_and_final_phase_structure():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "rakkhat", "Rakkhat"
    )

    assert {"Gold Pad Cycle", "Backyard Runner Phase", "Lunar Phase", "Final Phase"} <= _labels(projection)
    assert {"Pull", "Pads 3, 5, 7", "End of pad lap", "Within two lunar cycles"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Machine Gun" in strategy
    assert "blocks" in strategy["Machine Gun"].mitigation
    assert "Jump Knockback" in strategy
    assert "Block the jump" in strategy["Jump Knockback"].mitigation
