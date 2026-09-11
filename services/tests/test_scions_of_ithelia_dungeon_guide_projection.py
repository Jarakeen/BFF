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


def test_packmaster_projection_groups_split_boss_and_immunity_cycles():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "packmaster_rethelros", "Packmaster Rethelros and Malthil"
    )

    assert {"Split-Boss Main Phase", "Protective Totem Cycles"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Proximity Enrage" in strategy
    assert "separated" in strategy["Proximity Enrage"].mitigation.casefold()
    assert "Protective Totem" in strategy
    assert "immune" in strategy["Protective Totem"].mitigation.casefold()
    assert "Malthil Chase" in strategy
    assert "taunt" in strategy["Malthil Chase"].mitigation.casefold()


def test_anthelmir_projection_has_70_percent_transformation_and_axe_lanes():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "anthelmir_s_construct", "Anthelmir and Anthelmir's Construct"
    )

    assert {"Anthelmir + Construct", "Construct Transformation"} <= _labels(projection)
    assert "70% Construct" in _markers(projection)
    strategy = _strategy(projection)
    assert "Retrieve / Hurl Axe" in strategy
    assert "between" in strategy["Retrieve / Hurl Axe"].mitigation.casefold()
    assert "Cindermoths" in strategy
    assert "barrel" in strategy["Cindermoths"].mitigation.casefold()


def test_aradros_projection_has_50_percent_side_boss_intermission_and_floor_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "aradros_the_awakened", "Aradros the Awakened"
    )

    assert {"Main Phase I", "Side-Boss Intermission", "Main Phase II / Execute"} <= _labels(projection)
    assert "50%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Emblazoned Strike" in strategy
    assert "rotate" in strategy["Emblazoned Strike"].mitigation.casefold()
    assert "Smelter Helper" in strategy
    assert "optional" in strategy["Smelter Helper"].mitigation.casefold()


def test_shattered_champion_projection_has_glazier_cycles_and_healing_demand():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "shattered_champion", "Shattered Champion"
    )

    assert {"Main / Add Pressure", "Glazier Immunity Cycles", "Permanent Razor Glass Pressure"} <= _labels(projection)
    assert {"80%, 60%, 40%", "70%, 50%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Gaping Wound" in strategy
    assert "oblivion" in strategy["Gaping Wound"].mitigation.casefold()
    assert "Blind Path Glaziers" in strategy
    assert "immune" in strategy["Blind Path Glaziers"].mitigation.casefold()


def test_darkshard_projection_preserves_maelstrom_phase_carryover():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("darkshard", "Darkshard")

    assert {"Darkshard Main Phase", "Maxus the Many", "Champion of Atrocity", "Argonian Behemoth"} <= _labels(projection)
    assert {"80%", "60%", "40%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Obelisks and Spiderlings" in strategy
    assert "unwebbed" in strategy["Obelisks and Spiderlings"].mitigation.casefold()
    assert "Enraged Scream" in strategy
    assert "minder" in strategy["Enraged Scream"].mitigation.casefold()
    assert "Poison Bloom" in strategy
    assert "cleanse" in strategy["Poison Bloom"].mitigation.casefold()


def test_the_blind_projection_has_lane_intermissions_and_mobile_execute():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_blind", "The Blind")

    assert {
        "Main Phase / Deluge Setup",
        "Blind Shards / Gleaming Deluge",
        "Glass Remnant Intermission I",
        "Glass Remnant Intermission II",
        "Deluge Execute",
    } <= _labels(projection)
    assert {"80%", "60%", "40%", "20% to death"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Piercing Beam" in strategy
    assert "cannot be dodge rolled" in strategy["Piercing Beam"].mitigation.casefold()
    assert "Intermission Re-entry" in strategy
    assert "block" in strategy["Intermission Re-entry"].mitigation.casefold()
