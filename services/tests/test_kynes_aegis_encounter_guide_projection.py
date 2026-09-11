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


def test_yandir_projection_has_add_and_execute_phases_with_shield_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "yandir_the_butcher", "Yandir the Butcher"
    )

    assert {"100-50%", "50%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Hailstone Shield" in strategy
    assert "15-second" in strategy["Hailstone Shield"].mitigation
    assert "cannot be blocked or dodged" in strategy["Hailstone Shield"].mitigation
    assert "Totems" in strategy


def test_vrol_projection_has_45_second_pre_execute_and_50_percent_swap():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "captain_vrol", "Captain Vrol"
    )

    assert {"100-50%", "50%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Vrolsworn Conjurer" in strategy
    assert "boat runner" in strategy["Vrolsworn Conjurer"].mitigation
    assert "Shocking Harpoon" in strategy
    assert "Frigid Fog" in strategy


def test_falgravn_projection_has_floor_transitions_and_execute_cycles():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "lord_falgravn", "Lord Falgravn"
    )

    assert {"100-70%", "90%", "80%", "70-35%", "35%"} <= _markers(projection)
    assert {"Upper Deck / Njordal", "Middle Deck / Coagulants", "Cellar Execute"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Sanguine Prison" in strategy
    assert "8" in strategy["Sanguine Prison"].summary
    assert "Ichor Eruption" in strategy
    assert "30-second" in strategy["Ichor Eruption"].mitigation
    assert "Torturer / Prisoner Cycle" in strategy
    assert "upstairs DDs" in strategy["Torturer / Prisoner Cycle"].mitigation
