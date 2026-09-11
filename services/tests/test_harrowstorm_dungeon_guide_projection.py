from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_kjarg_projection_has_tornado_atronach_and_enrage_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("kjarg_the_tuskscraper", "Kjarg the Tuskscraper")
    strategy = _strategy(projection)
    assert "Tracking Ice Tornado" in strategy
    assert "kite" in strategy["Tracking Ice Tornado"].mitigation.casefold()
    assert "Frost Atronachs" in strategy
    assert "Enrage" in strategy


def test_skelga_projection_uses_fire_to_unfreeze_stranglers():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("sister_skelga", "Sister Skelga")
    strategy = _strategy(projection)
    assert "Player Fire AoE" in strategy
    assert "strangler" in strategy["Player Fire AoE"].mitigation.casefold()
    assert "Dark Drain Beams" in strategy


def test_vearogh_projection_has_tether_and_wraith_priorities():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("vearogh_the_shambler", "Vearogh the Shambler")
    strategy = _strategy(projection)
    assert "Draining Skeleton Tethers" in strategy
    assert "Wraith Adds" in strategy


def test_stormborn_projection_has_atronach_and_healing_check():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("stormborn_revenant", "Stormborn Revenant")
    strategy = _strategy(projection)
    assert "Storm Atronachs" in strategy
    assert "Ice Storm AoE" in strategy
    assert "healing" in strategy["Ice Storm AoE"].mitigation.casefold()


def test_icereach_coven_projection_keeps_grouped_rotation_and_interrupts():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("icereach_coven_boss", "Icereach Coven")
    assert {"Coven Sister Rotation", "Storm Surge Interrupt Cycles", "Mother Ciannait Burn"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Active Sister Enrage" in strategy
    assert "Storm Surge" in strategy
    assert "interrupt" in strategy["Storm Surge"].mitigation.casefold()


def test_hakgrym_projection_has_transformation_and_totem_priority():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("hakgrym_the_howler", "Hakgrym the Howler")
    assert {"Human Phase", "Werewolf Transformation"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Damage Totem" in strategy
    assert "Flesh Abominations" in strategy


def test_keeper_projection_has_lethal_kiln_rune_sequence():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("keeper_of_the_kiln", "Keeper of the Kiln")
    assert "Kiln Rune Cycles" in _labels(projection)
    strategy = _strategy(projection)
    assert "Kiln Rune Identification" in strategy
    assert "Boss Shield Break" in strategy
    assert "grapple" in strategy["Kiln Rune Identification"].mitigation.casefold()


def test_eternal_aegis_projection_has_reflection_spin_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("eternal_aegis", "Eternal Aegis")
    assert "Reflection Cycles" in _labels(projection)
    strategy = _strategy(projection)
    assert "Ring of Blades" in strategy
    assert "Lesser Aegis Reflections" in strategy


def test_ondagore_projection_has_gas_and_mender_shelter_phases():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("ondagore_the_mad", "Ondagore the Mad")
    assert {"Toxic Gas Escape", "Mender / Shelter Phase"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Bone Colossus" in strategy
    assert "Menders" in strategy
    assert "pillar" in strategy["Menders"].mitigation.casefold()


def test_kjalnar_projection_has_grave_dust_and_empowerment_priorities():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("kjalnar_tombskald", "Kjalnar Tombskald")
    strategy = _strategy(projection)
    assert "Grave Dust" in strategy
    assert "Imbued Skeleton Empowerment" in strategy
    assert "Kjalnar's Skull Totem" in strategy
