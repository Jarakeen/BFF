from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService

DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_risen_ruins_projection_has_orb_break():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("risen_ruins", "Risen Ruins")
    assert "Main Phase" in _labels(p)
    assert "Blood Orb Break" in _strategy(p)


def test_drozakar_projection_has_siphon_interrupt_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("dro_zakar", "Dro'zakar")
    assert "Siphon Hemoglobin" in _strategy(p)
    assert "heavy" in _strategy(p)["Siphon Hemoglobin"].mitigation.casefold()


def test_kujo_projection_has_geyser_cycle():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("kujo_kethba", "Kujo Kethba")
    assert "Eruption Cycles" in _labels(p)
    assert "Lava Geysers" in _strategy(p)


def test_nisaazda_projection_has_dual_boss_and_channel():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("nisaazda", "Nisaazda and Grundwulf")
    assert "Dual-Boss Phase" in _labels(p)
    assert "Sangiin's Thirst Channel" in _strategy(p)


def test_grundwulf_projection_has_heal_absorption():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("grundwulf", "Grundwulf")
    assert "Ghastly Wound" in _strategy(p)
    assert "absorption" in _strategy(p)["Ghastly Wound"].mitigation.casefold()


def test_selene_projection_has_poison_bolts():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("selene", "Selene")
    assert "Selene Beast Sequence" in _labels(p)
    assert "Poison Bolts" in _strategy(p)


def test_maarselok_flight_projection_has_strafe():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("maarselok_in_flight", "Maarselok in Flight")
    assert "Flight Phase" in _labels(p)
    assert "Blightbreath Strafe" in _strategy(p)


def test_cancroid_projection_has_seed_rotation():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("azureblight_cancroid", "Azureblight Cancroid")
    assert "Seed of Corruption Rotation" in _strategy(p)


def test_maarselok_perch_projection_has_lurcher_control():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("maarselok_on_his_perch", "Maarselok on His Perch")
    assert "Perch Phase" in _labels(p)
    assert "Azureblight Lurchers" in _strategy(p)


def test_maarselok_roost_projection_has_seed_cleanse():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("maarselok_in_his_roost", "Maarselok in His Roost")
    assert "Roost Final Phase" in _labels(p)
    assert "Azureblight Seed" in _strategy(p)
    assert "synergy" in _strategy(p)["Azureblight Seed"].mitigation.casefold()
