from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_ra_kotu_projection_has_main_phase_and_tank_tornado_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "ra_kotu", "Ra Kotu"
    )

    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Tornadoes" in strategy
    assert "tornado" in strategy["Tornadoes"].mitigation.casefold()
    assert "Heavy Cleave" in strategy
    assert "away from the raid" in strategy["Heavy Cleave"].mitigation.casefold()


def test_yokeda_split_projection_has_four_copy_interrupt_and_welwa_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "yokeda_split", "Yokeda Kai and Yokeda Rok'dun"
    )

    assert "Split Groups" in _labels(projection)
    strategy = _strategy(projection)
    assert "Split" in strategy
    assert "interrupt" in strategy["Split"].mitigation.casefold()
    assert "Welwa Adds" in strategy
    assert "controlled" in strategy["Welwa Adds"].mitigation
    assert "Side Wipe Enrage" in strategy


def test_warrior_projection_has_execute_shehai_and_stone_form_hm_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "the_warrior_celestial", "The Warrior"
    )

    assert {"Main Phase", "Execute"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Shehai Storm" in strategy
    assert "dodge" in strategy["Shehai Storm"].mitigation.casefold()
    assert "Stone Form" in strategy
    assert "Destructive Outbreak" in strategy["Stone Form"].mitigation
