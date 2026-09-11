from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_horvantud_projection_has_frontal_and_add_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("horvantud_the_fire_maw", "Horvantud the Fire Maw")
    s = _strategy(p)
    assert "Flame Breath" in s
    assert "away from the group" in s["Flame Breath"].mitigation.casefold()
    assert "Dremora Waves" in s


def test_ash_titan_projection_has_meteor_and_atronach_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("ash_titan_city_of_ash_ii", "Ash Titan")
    s = _strategy(p)
    assert "Meteor Strikes" in s
    assert "Burning Atronachs" in s
    assert "cleave" in s["Heavy Cleave"].mitigation.casefold()


def test_valkyn_skoria_projection_has_platform_execute():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("valkyn_skoria_person", "Valkyn Skoria")
    assert {"Platform Cycle", "Lava Execute"} <= _labels(p)
    s = _strategy(p)
    assert "Lava Platforms" in s
    assert "safe platforms" in s["Lava Platforms"].mitigation.casefold()


def test_ruzozuzalpamaz_projection_has_cocoon_rescue():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("ruzozuzalpamaz", "Ruzozuzalpamaz")
    s = _strategy(p)
    assert "Web Cocoon" in s
    assert "synergy" in s["Web Cocoon"].mitigation.casefold()
    assert "Chasing AoE" in s


def test_ilambris_projection_keeps_brothers_and_amalgam_one_encounter():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("ilambris_amalgam", "Brothers Ilambris and Ilambris Amalgam")
    assert {"Brothers Ilambris", "Ilambris Amalgam"} <= _labels(p)
    s = _strategy(p)
    assert "Skeleton Waves" in s
    assert "Rain of Fire" in s


def test_nerieneth_projection_has_ebony_blade_hard_mode_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("nerien_eth", "Nerien'eth")
    assert {"Lich Phase", "Ebony Blade Phase"} <= _labels(p)
    s = _strategy(p)
    assert "Students / Hard Mode" in s
    assert "four students" in s["Students / Hard Mode"].mitigation.casefold()
    assert "Drain Shield" in s
