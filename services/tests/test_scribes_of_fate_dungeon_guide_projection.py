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


def test_kovan_projection_has_shadow_cycles_and_poison_spacing():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("kovan_giryon", "Kovan Giryon")

    assert {"Main Phase / Teleport Pressure", "Shadow Add Cycles"} <= _labels(projection)
    assert "65%, 45%, 20%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Poison Phase" in strategy
    assert "soft stack" in strategy["Poison Phase"].mitigation.casefold()
    assert "Teleport Rectangles" in strategy
    assert "clone" in strategy["Teleport Rectangles"].mitigation.casefold()


def test_roksa_projection_has_darkness_cycles_orb_interrupts_and_triple_hm_beam():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("roksa_the_warped", "Roksa the Warped")

    assert {"Main Phase / Darklight Orbs", "Darkness Cycles"} <= _labels(projection)
    assert "70%, 40%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Darklight Orbs" in strategy
    assert "interrupt" in strategy["Darklight Orbs"].mitigation.casefold()
    assert "Post-Darkness Tank Beam" in strategy
    assert "triple" in strategy["Post-Darkness Tank Beam"].mitigation.casefold()


def test_lladi_projection_has_poison_storm_cycles_and_skeever_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "matriarch_lladi_telvanni", "Matriarch Lladi Telvanni"
    )

    assert {"Main Phase / Peryite Pressure", "Poison Storm / Time Stop Cycles"} <= _labels(projection)
    assert "70%, 35%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Choking Pestilence / Poison Storm" in strategy
    assert "time-stop" in strategy["Choking Pestilence / Poison Storm"].mitigation.casefold()
    assert "Hard Mode Skeevers" in strategy
    assert "taunts do not" in strategy["Hard Mode Skeevers"].mitigation.casefold()


def test_naqri_projection_has_three_codex_thresholds_and_two_hm_soaks():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("riftmaster_naqri", "Riftmaster Naqri")

    assert {"Main Phase / Codex Pressure", "Hidden Codex Cycles"} <= _labels(projection)
    assert "80%, 55%, 35%" in _markers(projection)
    strategy = _strategy(projection)
    assert "Hidden Codex" in strategy
    assert "two hidden codices" in strategy["Hidden Codex"].mitigation.casefold()
    assert "Unstable Literature" in strategy
    assert "two simultaneous soaks" in strategy["Unstable Literature"].mitigation.casefold()


def test_ozezan_projection_preserves_lava_space_for_suction_and_hm_atronachs():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "ozezan_the_inferno", "Ozezan the Inferno"
    )

    assert {"Main Phase / Lava Placement", "Central Suction Check", "Hard Mode Iron Atronachs"} <= _labels(projection)
    assert {"40%, 20%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Persistent Lava Pools" in strategy
    assert "suction" in strategy["Persistent Lava Pools"].mitigation.casefold()
    assert "Tracking Lasers" in strategy
    assert "everyone" in strategy["Tracking Lasers"].mitigation.casefold()


def test_valinna_projection_groups_lamikhai_and_preserves_three_room_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("valinna", "Valinna and Lamikhai")

    assert {"Room I / Lamikhai", "Room II / Valinna and Lamikhai", "Room III / Valinna Execute"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Lamikhai Enrage / Frost Trap" in strategy
    assert "frost trap" in strategy["Lamikhai Enrage / Frost Trap"].mitigation.casefold()
    assert "Immolation Trap" in strategy
    assert "stay inside" in strategy["Immolation Trap"].mitigation.casefold()
    assert "Ensnaring Spiders" in strategy
    assert "priority rescue" in strategy["Ensnaring Spiders"].mitigation.casefold()
