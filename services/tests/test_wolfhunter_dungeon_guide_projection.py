from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_jailer_melitus_projection_has_interrupt_and_geysers():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("jailer_melitus", "Jailer Melitus")
    strategy = _strategy(projection)
    assert "Pin / Charged Execution" in strategy
    assert "interrupt" in strategy["Pin / Charged Execution"].mitigation.casefold()
    assert "Bloody Geysers" in strategy


def test_hedge_maze_guardian_projection_has_both_maze_phases():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("hedge_maze_guardian", "Hedge Maze Guardian")
    assert {"Boss Phase I", "Spriggan Maze I", "Spriggan Maze II"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Strangler Snare" in strategy
    assert "interrupt" in strategy["Strangler Snare"].mitigation.casefold()


def test_mylenne_projection_has_pounce_and_lightning_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("mylenne_moon_caller", "Mylenne Moon-Caller")
    strategy = _strategy(projection)
    assert "Pounce Pin" in strategy
    assert "interrupt" in strategy["Pounce Pin"].mitigation.casefold()
    assert "Shock Warden Lightning" in strategy


def test_archivist_projection_has_symbols_of_xarxes():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("archivist_ernarde", "Archivist Ernarde")
    strategy = _strategy(projection)
    assert "Symbols of Xarxes" in strategy
    assert "matching rune" in strategy["Symbols of Xarxes"].mitigation.casefold()


def test_vykosa_projection_has_hard_mode_escalation():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("vykosa_the_ascendant", "Vykosa the Ascendant")
    assert "Hard Mode Escalation" in _labels(projection)
    strategy = _strategy(projection)
    assert "Werewolf Add Waves" in strategy
    assert "Restrained Wolves" in strategy


def test_wyrd_sisters_projection_has_grouped_aura_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("wyrd_sisters", "Wyrd Sisters")
    strategy = _strategy(projection)
    assert "Sister Auras" in strategy
    assert "separated" in strategy["Sister Auras"].mitigation.casefold()


def test_aghaedh_projection_has_seasonal_color_check():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("aghaedh_of_the_solstice", "Aghaedh of the Solstice")
    strategy = _strategy(projection)
    assert "Seasonal Colors" in strategy
    assert "matching" in strategy["Seasonal Colors"].mitigation.casefold()
    assert "Lurcher Adds" in strategy


def test_dagrund_projection_has_upheaval_and_add_priority():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("dagrund_the_bulky", "Dagrund the Bulky")
    strategy = _strategy(projection)
    assert "Upheaval" in strategy
    assert "dodge" in strategy["Upheaval"].mitigation.casefold()
    assert "Elemental Adds" in strategy


def test_tarcyr_projection_has_hunt_and_interrupt():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("tarcyr", "Tarcyr")
    assert {"Combat Phase", "Shrouding Mist Hunt"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Shrouding Mist" in strategy
    assert "stealth" in strategy["Shrouding Mist"].mitigation.casefold()
    assert "Lightning Prance" in strategy


def test_balorgh_projection_has_elemental_arena_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("balorgh", "Balorgh")
    assert {"Balorgh Combat", "Hunt / Trap Phase"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Lightning Water" in strategy
    assert "safe island" in strategy["Lightning Water"].mitigation.casefold()
    assert "Poison Plants" in strategy
    assert "Fire Remnant" in strategy
