from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService

DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_lizabet_charnis_projection_has_wave_control():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("lizabet_charnis", "Lizabet Charnis")
    s = _strategy(p)
    assert "Summoned Waves" in _labels(p)
    assert "Bone Colossus Adds" in s
    assert "Flying Skulls" in s


def test_cadaverous_menagerie_projection_has_grip_and_fungi():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("cadaverous_menagerie", "Cadaverous Menagerie")
    s = _strategy(p)
    assert "Senche Death Grip" in s
    assert "Volatile Fungi" in s


def test_caluurion_projection_has_relic_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("caluurion", "Caluurion")
    s = _strategy(p)
    assert "Elemental Relics" in s
    assert "bonefiend" in s["Elemental Relics"].mitigation.casefold()


def test_ulfnor_projection_has_sabina_priority():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("ulfnor", "Ulfnor and Sabina Cedus")
    s = _strategy(p)
    assert "Haunting Spectre" in s
    assert "sabina" in s["Haunting Spectre"].mitigation.casefold()


def test_thurvokun_projection_has_orryn_interrupt_and_breath():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("orryn_the_black", "Orryn the Black and Thurvokun")
    s = _strategy(p)
    assert "Orryn Channel" in s
    assert "interrupt" in s["Orryn Channel"].mitigation.casefold()
    assert "Plague Breath" in s


def test_twin_ogre_projection_has_tremor_shelter():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("orzun_the_foul_smelling", "Orzun the Foul-Smelling and Rinaerus the Rancid")
    s = _strategy(p)
    assert "Terrorizing Tremor" in s
    assert "ice spikes" in s["Terrorizing Tremor"].mitigation.casefold()


def test_doylemish_projection_has_stony_gaze_response():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("doylemish_ironheart", "Doylemish Ironheart")
    s = _strategy(p)
    assert "Stony Gaze" in s
    assert "petrified" in s["Stony Gaze"].mitigation.casefold()


def test_aldis_projection_has_vent_and_water_rules():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("matriarch_aldis", "Matriarch Aldis")
    s = _strategy(p)
    assert "Ice Vent" in s
    assert "Ice Water" in s


def test_mortieu_projection_has_antidote_and_grates():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("plague_concocter_mortieu", "Plague Concocter Mortieu")
    s = _strategy(p)
    assert "Jorvuld Antidote" in s
    assert "Poison Grates" in s


def test_zaan_projection_has_twenty_percent_cycles_and_poison_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("zaan_the_scalecaller", "Zaan the Scalecaller")
    s = _strategy(p)
    assert "Atronach Cycles" in _labels(p)
    assert "Fire Cage Beam" in s
    assert "Poison Wave" in s
