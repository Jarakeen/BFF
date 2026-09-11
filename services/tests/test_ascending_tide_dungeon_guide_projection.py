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


def test_maligalig_projection_has_flood_cycles_and_static_management():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("maligalig", "Maligalig")
    assert {"Main Phase I", "Surging Waters I", "Surging Waters II", "Execute"} <= _labels(projection)
    assert {"~70%", "~35%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Storm Cell" in strategy
    assert "roaming storm" in strategy["Storm Cell"].mitigation.casefold()
    assert "Building Static" in strategy
    assert "water" in strategy["Building Static"].mitigation.casefold()


def test_sarydil_projection_has_two_add_phases_and_trap_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("sarydil", "Sarydil")
    assert {"Main Phase I", "Archer / Trap Phase I", "Reinforced Add Phase"} <= _labels(projection)
    assert {"~70%", "~35%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Target Mark" in strategy
    assert "outside edge" in strategy["Target Mark"].mitigation.casefold()
    assert "Pinpoint" in strategy
    assert "interrupt" in strategy["Pinpoint"].mitigation.casefold()


def test_varallion_projection_has_gryphon_overlap_and_hard_mode_execute():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("varallion", "Varallion")
    assert {"Main Phase", "Gryphon Overlap", "Hard Mode Kargaeda Execute"} <= _labels(projection)
    assert "~30%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Crashing Waves / Sea Orbs" in strategy
    assert "multiple sides" in strategy["Crashing Waves / Sea Orbs"].mitigation.casefold()
    assert "Hard Mode Tether" in strategy
    assert "stay close" in strategy["Hard Mode Tether"].mitigation.casefold()


def test_bradiggan_projection_has_possession_cycles_and_pair_bombs():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("foreman_bradiggan", "Foreman Bradiggan")
    assert {"Main Phase I", "Possession / Colossus I", "Possession / Colossus II", "Hard Mode Soul-Bomb Execute"} <= _labels(projection)
    assert {"~60%", "~30%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Paralyzing Fear" in strategy
    assert "dodge" in strategy["Paralyzing Fear"].mitigation.casefold()
    assert "Soul Bomb" in strategy
    assert "exactly two" in strategy["Soul Bomb"].mitigation.casefold()


def test_nazaray_projection_has_kindred_cycles_and_empowerment_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("nazaray", "Nazaray")
    assert {"Main Phase", "Kindred Spirit Cycles"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Kindred Spirit" in strategy
    assert "opposite" in strategy["Kindred Spirit"].mitigation.casefold()
    assert "Liquidate / Blue Empowerment" in strategy
    assert "immune" in strategy["Liquidate / Blue Empowerment"].mitigation.casefold()


def test_numirril_projection_has_hulk_thresholds_and_bile_management():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("captain_numirril", "Captain Numirril")
    assert {"Main Phase I", "Drowned Hulk I", "Main Phase II", "Hard Mode Double Hulk"} <= _labels(projection)
    assert {"~80%", "~40%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Tidal Waves" in strategy
    assert "wash away bile" in strategy["Tidal Waves"].mitigation.casefold()
    assert "Drown" in strategy
    assert "losing aggro" in strategy["Drown"].mitigation.casefold()
