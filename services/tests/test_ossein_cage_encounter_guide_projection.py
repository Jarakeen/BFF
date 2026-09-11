from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_shapers_projection_has_portal_cycle_and_add_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "shaper_of_flesh", "Shapers of Flesh"
    )

    assert {"Main Arena", "Carrion Portal", "Post-Portal Adds"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Fleshspawn Merge" in strategy
    assert "Flesh Abomination" in strategy["Fleshspawn Merge"].mitigation
    assert "Carrion Portal" in strategy
    assert "Channeler" in strategy["Carrion Portal"].mitigation


def test_jynorah_skorkhif_projection_has_clashes_unblockable_rays_and_sync_kill():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "jynorah_skorkhif", "Jynorah and Skorkhif"
    )

    assert {"Split Boss Phase", "Titanic Clash I", "Titanic Clash II", "Synchronized Kill"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Heat Ray" in strategy
    assert "unblockable" in strategy["Heat Ray"].mitigation.casefold()
    assert "Sparking Blazing Enfeeblement" in strategy
    assert "Seeking Surges" in strategy
    assert "Synchronized Kill" in strategy
    assert "15 seconds" in strategy["Synchronized Kill"].mitigation


def test_kazpian_projection_has_platform_portal_cycle_and_key_raid_mechanics():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "overfiend_kazpian", "Overfiend Kazpian"
    )

    assert {"Main Platform", "Carrion Portal", "Platform Transition"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Agonizer Bomb" in strategy
    assert "only the initial target" in strategy["Agonizer Bomb"].mitigation
    assert "Torturous Chains" in strategy
    assert "Giant Sword" in strategy["Torturous Chains"].mitigation
    assert "Biting Blaze" in strategy
    assert "Kazpian Ally Proximity Enrage" in strategy
    assert "separated" in strategy["Kazpian Ally Proximity Enrage"].mitigation
