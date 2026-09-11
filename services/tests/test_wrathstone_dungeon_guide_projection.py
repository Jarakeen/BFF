from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_scavenging_maw_projection_has_hunt_and_interrupt_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_scavenging_maw", "The Scavenging Maw")
    assert "Hunt Cycle" in _labels(projection)
    strategy = _strategy(projection)
    assert "Hunting Ambush" in strategy
    assert "interrupt" in strategy["Hunting Ambush"].mitigation.casefold()


def test_weeping_woman_projection_has_glaciation_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_weeping_woman", "The Weeping Woman")
    strategy = _strategy(projection)
    assert "Glaciation" in strategy
    assert "move" in strategy["Glaciation"].mitigation.casefold()


def test_dark_orb_projection_has_priority_cycles():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("dark_orb", "Dark Orb")
    assert "Colored Orb Cycles" in _labels(projection)
    strategy = _strategy(projection)
    assert "Colored Orbs" in strategy
    assert "orb" in strategy["Colored Orbs"].mitigation.casefold()


def test_king_narilmor_projection_has_reflection_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("king_narilmor", "King Narilmor")
    assert "Reflection Cycles" in _labels(projection)
    strategy = _strategy(projection)
    assert "Narilmor Reflections" in strategy
    assert "real" in strategy["Narilmor Reflections"].mitigation.casefold()


def test_symphony_projection_has_phalanx_and_orb_priorities():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("symphony_of_blades", "Symphony of Blades")
    strategy = _strategy(projection)
    assert "Auroran Phalanx" in strategy
    assert "Colored Orbs" in strategy


def test_icestalker_projection_has_knockup_interrupt():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("icestalker", "Icestalker")
    strategy = _strategy(projection)
    assert "Knock-up Follow-up" in strategy
    assert "interrupt" in strategy["Knock-up Follow-up"].mitigation.casefold()


def test_tzogvin_projection_has_spread_whirlwind_and_tether_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("warlord_tzogvin", "Warlord Tzogvin")
    strategy = _strategy(projection)
    assert {"Fire Greatsword Spread", "Frost Whirlwinds", "Player Tether"} <= set(strategy)


def test_vault_protector_projection_has_laser_thresholds():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("vault_protector", "Vault Protector")
    assert {"One-Laser Shield", "Two-Laser Shield", "Four-Laser Shield"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Rotating Laser Beams" in strategy
    assert "safe" in strategy["Rotating Laser Beams"].mitigation.casefold()


def test_rizzuk_projection_has_spread_interrupt_and_avalanche_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("rizzuk_bonechill", "Rizzuk Bonechill")
    strategy = _strategy(projection)
    assert {"Glacial Prison Curse", "Frost Bolt Channel", "Avalanche Ice Ring"} <= set(strategy)


def test_stonekeeper_projection_has_skeevaton_protocol():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_stonekeeper", "The Stonekeeper")
    assert {"Gauntlet Phase I", "Skeevaton Extermination Protocol", "Gauntlet Phase II"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Skeevaton Protocol" in strategy
    assert "Shock Conveyors" in strategy["Skeevaton Protocol"].mitigation
