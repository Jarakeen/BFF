from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_sithera_projection_has_light_and_interrupt_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("sithera", "Sithera")
    assert {"Outer Light", "Middle Brazier", "Final Brazier"} <= _labels(p)
    s = _strategy(p)
    assert "Power Up Channel" in s
    assert "interrupt" in s["Power Up Channel"].mitigation.casefold()


def test_khephidaen_projection_has_brazier_control():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("khephidaen", "Khephidaen the Spiderkith")
    s = _strategy(p)
    assert "Brazier Light" in s
    assert "active light" in s["Brazier Light"].mitigation.casefold()


def test_votary_projection_has_feed_interrupt_and_blast_escape():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("votary_of_velidreth", "Votary of Velidreth")
    s = _strategy(p)
    assert {"Feeding Channel", "Expanding Blast", "Poison Circles"} <= set(s)
    assert "interrupt" in s["Feeding Channel"].mitigation.casefold()


def test_dranos_projection_has_shadow_orb_cycle():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("dranos_velador", "Dranos Velador")
    assert "Shadow Orb Cycle" in _labels(p)
    s = _strategy(p)
    assert "Essence Orbs" in s
    assert "three shadow" in s["Essence Orbs"].mitigation.casefold()


def test_velidreth_projection_has_hunt_and_devour_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("velidreth", "Velidreth the Lady of Lace")
    assert "Shadow Hunt" in _labels(p)
    s = _strategy(p)
    assert {"Shadow Sense", "Devour", "Venom Sacs"} <= set(s)
    assert "stop moving" in s["Shadow Sense"].mitigation.casefold()


def test_zatzu_projection_has_block_and_jump_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("zatzu_the_spine_breaker", "Zatzu the Spine-Breaker")
    s = _strategy(p)
    assert {"Rock Throw", "Leaping Impact"} <= set(s)
    assert "block" in s["Rock Throw"].mitigation.casefold()


def test_mighty_chudan_projection_has_charge_alignment():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("mighty_chudan", "The Mighty Chudan")
    s = _strategy(p)
    assert {"Mighty Charge", "Spit"} <= set(s)
    assert "line" in s["Mighty Charge"].mitigation.casefold()


def test_xal_nur_projection_has_spice_and_wamasu_plan():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("xal_nur_the_slaver", "Xal-Nur the Slaver")
    s = _strategy(p)
    assert {"Swamp Spice", "Chained Wamasu", "Boss Charge"} <= set(s)
    assert "geyser" in s["Swamp Spice"].mitigation.casefold()


def test_tree_minder_projection_has_totems_reveal_and_amber():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("tree_minder_na_kesh", "Tree-Minder Na-Kesh")
    s = _strategy(p)
    assert {"Totems", "Hist Sap / Statue Reveal", "Amber Plasm", "Blistering Amber"} <= set(s)
    assert "reveal" in s["Hist Sap / Statue Reveal"].mitigation.casefold()
