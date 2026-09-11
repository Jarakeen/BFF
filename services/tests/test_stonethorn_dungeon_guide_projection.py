from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_dread_tindulra_projection_has_breath_and_broodling_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("dread_tindulra", "Dread Tindulra")
    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Death Breath" in strategy
    assert "cone" in strategy["Death Breath"].mitigation.casefold()
    assert "Death Hound Broodlings" in strategy


def test_blood_twilight_projection_has_execute_beam():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("blood_twilight", "Blood Twilight")
    assert {"Gargoyle Awakening Cycles", "Group Beam Execute"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Group Beam" in strategy
    assert "spread" in strategy["Group Beam"].mitigation.casefold()


def test_vaduroth_projection_has_sickle_and_add_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("vaduroth", "Vaduroth")
    strategy = _strategy(projection)
    assert "Thrown Sickle" in strategy
    assert "corpse" in strategy["Thrown Sickle"].mitigation.casefold()
    assert "Reanimated Adds" in strategy


def test_talfyg_projection_has_frozen_gargoyle_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("talfyg", "Talfyg")
    strategy = _strategy(projection)
    assert "Frozen Gargoyles" in strategy
    assert "gargoyle" in strategy["Frozen Gargoyles"].mitigation.casefold()


def test_lady_thorn_projection_has_bat_swarm_transition():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("lady_thorn", "Lady Thorn")
    assert {"Main Blood Phase", "Bat Swarm / Scavenger Synergy"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Bat Swarm" in strategy
    assert "synergy" in strategy["Bat Swarm"].mitigation.casefold()


def test_exarch_kraglen_projection_has_blood_rage_interrupt():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("exarch_kraglen", "Exarch Kraglen")
    strategy = _strategy(projection)
    assert "Blood Rage" in strategy
    assert "interrupt" in strategy["Blood Rage"].mitigation.casefold()


def test_stone_behemoth_projection_has_spread_and_burst_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("stone_behemoth", "Stone Behemoth")
    strategy = _strategy(projection)
    assert "Essence Explosion" in strategy
    assert "Player Lightning AoEs" in strategy
    assert "spread" in strategy["Player Lightning AoEs"].mitigation.casefold()


def test_arkasis_projection_has_transformations_and_evolved_execute():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "arkasis_the_mad_alchemist", "Arkasis the Mad Alchemist"
    )
    assert {
        "Human Arkasis I",
        "Werewolf Behemoth Intermission I",
        "Human Arkasis II",
        "Werewolf Behemoth Intermission II",
        "Evolved Arkasis Execute",
    } <= _labels(projection)
    strategy = _strategy(projection)
    assert "Stone Husk Control" in strategy
    assert "Bonecrusher" in strategy["Stone Husk Control"].mitigation
    assert "Lightning AoE" in strategy
