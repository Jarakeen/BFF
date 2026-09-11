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


def test_hunter_killers_projection_has_split_scarabs_and_execute_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "hunter_killers", "Hunter-Killer Negatrix and Positrox"
    )

    assert {"Split-Tank Main Phase", "Scarabs", "Paired Execute"} <= _labels(projection)
    assert {"Pull", "75%", "50%", "25%", "~20% each"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Boss Separation" in strategy
    assert "split" in strategy["Boss Separation"].mitigation.casefold()
    assert "Sphere Shield Break" in strategy
    assert "Take Aim" in strategy


def test_pinnacle_projection_has_shades_centurions_and_upstairs_timeout():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "pinnacle_factotum", "Pinnacle Factotum"
    )

    assert {"Main Floor Phase", "Shade Sequence Added", "Charging Centurion Added", "Upper Platform Cycle"} <= _labels(projection)
    assert {"Pull", "75%", "40%", "~90s after prior completion"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Charging Up" in strategy
    assert "interrupt" in strategy["Charging Up"].mitigation.casefold()
    assert "Upper Platform Timeout" in strategy
    assert "60-second" in strategy["Upper Platform Timeout"].mitigation


def test_archcustodian_projection_is_pylon_driven():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "archcustodian", "Archcustodian"
    )

    assert {"Shielded Walk", "Shock Pylon Stun"} <= _labels(projection)
    assert {"Pull / after each stun", "Pylon activation"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Shock Pylon" in strategy
    assert "stunned" in strategy["Shock Pylon"].mitigation
    assert "Spinning Blades" in strategy


def test_refabrication_committee_projection_has_three_stun_burn_thresholds():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "refabrication_committee", "Refabrication Committee"
    )

    assert {"Split Bosses", "Beam-Stun Burn"} <= _labels(projection)
    assert {"Pull", "69%", "39%", "25%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Tank Boss Swap" in strategy
    assert "Ten stacks" in strategy["Tank Boss Swap"].mitigation
    assert "Bombers" in strategy
    assert "Exploding Ruined Fabricants" in strategy


def test_assembly_general_projection_has_recharges_and_meteor_execute():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "assembly_general", "Assembly General"
    )

    assert {"Main Arm Phase", "Recharge / Terminals", "Meteor Execute"} <= _labels(projection)
    assert {"Pull", "85%", "65%", "45%", "25%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Stomp" in strategy
    assert "double-stomps" in strategy["Stomp"].mitigation
    assert "Terminals" in strategy
    assert "Stop hitting Assembly General" in strategy["Terminals"].mitigation
