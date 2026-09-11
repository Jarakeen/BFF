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


def test_jerensi_projection_has_immunity_cycles_and_four_player_execute_stack():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "executioner_jerensi", "Executioner Jerensi"
    )

    assert {"Main Phase", "Shadow Ward / Execute Cycles"} <= _labels(projection)
    assert "80%, 50%, 30%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Execute" in strategy
    assert "all four" in strategy["Execute"].mitigation.casefold()
    assert "Jailer and Torturer Adds" in strategy
    assert "interrupt" in strategy["Jailer and Torturer Adds"].mitigation.casefold()


def test_vandorallen_projection_has_dedicated_kite_and_icy_dome_spider_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "prime_sorcerer_vandorallen", "Prime Sorcerer Vandorallen"
    )

    assert {"Main / Kite Phase", "Iron Charge / Icy Dome"} <= _labels(projection)
    assert "90%, 66%, 45%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Storm Bolt" in strategy
    assert "dedicated" in strategy["Storm Bolt"].mitigation.casefold()
    assert "Iron Atronach Spiders" in strategy
    assert "icy dome" in strategy["Iron Atronach Spiders"].mitigation.casefold()


def test_squall_projection_preserves_slow_burn_element_and_orb_economy():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "squall_of_retribution", "Squall of Retribution"
    )

    assert {"Fire Infusion", "Ice Infusion", "Lightning Infusion"} <= _labels(projection)
    assert {"95%", "65%", "32%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Elemental Orbs" in strategy
    assert "slow the burn" in strategy["Elemental Orbs"].mitigation.casefold()
    assert "Coordinated Slash" in strategy
    assert "dodge" in strategy["Coordinated Slash"].mitigation.casefold()


def test_garvin_projection_has_boulder_bowling_and_pre_scream_damage_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "garvin_the_tracker", "Garvin the Tracker"
    )

    assert {"Main / Boulder Setup", "Duneripper Bowling", "Scream / Execute Pressure"} <= _labels(projection)
    assert {"80%, 50%, 40% HM", "30%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Noxious Boulder" in strategy
    assert "unaggroed" in strategy["Noxious Boulder"].mitigation.casefold()
    assert "Monstrous Dunerippers" in strategy
    assert "do not taunt" in strategy["Monstrous Dunerippers"].mitigation.casefold()
    assert "Venom Eruption" in strategy
    assert "line of sight" in strategy["Venom Eruption"].mitigation.casefold()


def test_noriwen_projection_has_alcunar_gryphon_and_tank_proximity_assignments():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("noriwen", "Noriwen")

    assert {
        "Main / Chain Pull",
        "Alcunar Phase I",
        "Flame Gryphon Intermission",
        "Noriwen + Flame Gryphons",
        "Alcunar Execute",
    } <= _labels(projection)
    assert {"70% to 50%", "50%", "40%", "20% to death"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Chain Pull" in strategy
    assert "melee range" in strategy["Chain Pull"].mitigation.casefold()
    assert "Wing Gust" in strategy
    assert "extra room" in strategy["Wing Gust"].mitigation.casefold()


def test_orpheon_projection_has_planemeld_movement_add_phases_and_tank_dragging():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "orpheon_the_tactician", "Orpheon the Tactician"
    )

    assert {
        "Planemeld Main Phase",
        "Planemeld Move / Add Phase I",
        "Planemeld Move / Add Phase II",
        "Planemeld Move / Add Phase III",
        "Endless Planemeld Movement",
    } <= _labels(projection)
    assert {"80%", "50%", "30%", "20% to death"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Arcane Planemeld" in strategy
    assert "drags orpheon" in strategy["Arcane Planemeld"].mitigation.casefold()
    assert "Add Phase" in strategy
    assert "chains" in strategy["Add Phase"].mitigation.casefold()
    assert "Forbidden Knowledge" in strategy
    assert "unblockable" in strategy["Forbidden Knowledge"].mitigation.casefold()
