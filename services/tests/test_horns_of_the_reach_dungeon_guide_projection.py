from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_mathgamain_projection_has_frontal_and_add_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("mathgamain", "Mathgamain")
    s = _strategy(p)
    assert "Frontal Cone" in s
    assert "faces mathgamain away" in s["Frontal Cone"].mitigation.casefold()
    assert "Add Waves" in s


def test_caillaoife_projection_has_three_forest_thresholds():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("caillaoife", "Caillaoife")
    assert {"Forest I", "Forest II", "Forest III"} <= _labels(p)
    assert "Icy Root" in _strategy(p)


def test_stoneheart_projection_has_execute_add_pressure():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("stoneheart", "Stoneheart")
    assert "Stone Add Execute" in _labels(p)
    s = _strategy(p)
    assert "Resurrected Stone Adds" in s
    assert "quickly" in s["Resurrected Stone Adds"].mitigation.casefold()


def test_galchobhar_projection_has_vents_platforms_and_shalks():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("galchobhar", "Galchobhar")
    s = _strategy(p)
    assert {"Fire Vents", "Weapon Throw", "Fire Shalk Lava Ball"} <= set(s)
    assert "platform" in s["Weapon Throw"].mitigation.casefold()


def test_gherig_projection_has_interruptible_chain_root():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("gherig_bullblood", "Gherig Bullblood and His Attendants")
    s = _strategy(p)
    assert "Chain Root" in s
    assert "interrupt" in s["Chain Root"].mitigation.casefold()


def test_earthgore_projection_has_lava_stonefall_and_copies():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("earthgore_amalgam", "Earthgore Amalgam")
    s = _strategy(p)
    assert {"Lava AoE", "Stonefall", "Amalgam Copies"} <= set(s)
    assert "wall" in s["Lava AoE"].mitigation.casefold()


def test_morrigh_projection_has_fifty_percent_siege_shelter():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("morrigh_bullblood", "Morrigh Bullblood")
    assert "Siege Shelter" in _labels(p)
    s = _strategy(p)
    assert "Siege Shield" in s
    assert "protective shield" in s["Siege Shield"].mitigation.casefold()


def test_siege_mammoth_projection_has_block_stomp():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("siege_mammoth", "Siege Mammoth")
    assert "Stomp Pressure" in _labels(p)
    s = _strategy(p)
    assert "Stomp" in s
    assert "block" in s["Stomp"].mitigation.casefold()


def test_cernunnon_projection_has_two_oathbound_cycles():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("cernunnon", "Cernunnon")
    assert {"Oath-Bound I", "Cernunnon I", "Oath-Bound II"} <= _labels(p)
    s = _strategy(p)
    assert "Oath-Bound Souls" in s
    assert "Ice Comet" in s


def test_deathlord_projection_has_corpse_cleanse_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("deathlord_bjarfrud_skjoralmor", "Deathlord Bjarfrud Skjoralmor")
    s = _strategy(p)
    assert {"Corpse Cleanse", "Corpse Detonation", "Frontal Breath"} <= set(s)
    assert "cleanse" in s["Corpse Detonation"].mitigation.casefold()


def test_domihaus_projection_has_shout_thresholds_and_execute():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("domihaus_the_bloody_horned", "Domihaus the Bloody-Horned")
    assert {"Pillar Shouts", "Shielded Execute"} <= _labels(p)
    s = _strategy(p)
    assert "Domihaus Shout" in s
    assert "same assigned pillar" in s["Domihaus Shout"].mitigation.casefold()
    assert "Suck In and Melt" in s
