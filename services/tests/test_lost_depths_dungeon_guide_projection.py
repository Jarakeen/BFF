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


def test_corruption_of_stone_projection_has_shelter_cycles_and_add_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "corruption_of_stone", "Corruption of Stone"
    )

    assert {"Main Phase", "Hard Mode Stone Aura Execute"} <= _labels(projection)
    assert {"75%", "50%", "25%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Ground Slam Shelter" in strategy
    assert "pillar" in strategy["Ground Slam Shelter"].mitigation.casefold()
    assert "Stone Atronachs" in strategy
    assert "interrupt" in strategy["Stone Atronachs"].mitigation.casefold()


def test_corruption_of_root_projection_has_distributor_and_space_management():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "corruption_of_root", "Corruption of Root"
    )

    assert {"Main / Add Cycle", "Distributor Split Cycle"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Spriggan Death Zones" in strategy
    assert "permanent" in strategy["Spriggan Death Zones"].mitigation.casefold()
    assert "Hard Mode Faun / Tree Enrage" in strategy
    assert "red-glowing" in strategy["Hard Mode Faun / Tree Enrage"].mitigation.casefold()


def test_archdruid_devyric_projection_has_two_bear_transformations():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "archdruid_devyric", "Archdruid Devyric"
    )

    assert {"Human Phase I", "Bear Phase I", "Human Phase II", "Bear Execute"} <= _labels(projection)
    assert {"70% transition; heals to about 80%", "20% transition; heals to about 40%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Bear Charge / Stone Totems" in strategy
    assert "totem" in strategy["Bear Charge / Stone Totems"].mitigation.casefold()
    assert "Bear Lightning Breath" in strategy
    assert "away" in strategy["Bear Lightning Breath"].mitigation.casefold()


def test_euphotic_gatekeeper_projection_preserves_burrow_and_molt_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "the_euphotic_gatekeeper", "The Euphotic Gatekeeper"
    )

    assert "Main / Pangrit Burrow Cycle" in _labels(projection)
    strategy = _strategy(projection)
    assert "Pangrit Pits / Poison Synergy" in strategy
    assert "burrow" in strategy["Pangrit Pits / Poison Synergy"].mitigation.casefold()
    assert "Molting / Untargetable Window" in strategy
    assert "untargetable" in strategy["Molting / Untargetable Window"].mitigation.casefold()


def test_varzunon_projection_has_sacrifice_growth_and_healing_pressure():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("varzunon", "Varzunon")

    assert "Main / Skeletal Sacrifice Cycle" in _labels(projection)
    strategy = _strategy(projection)
    assert "Skeletal Sacrifices" in strategy
    assert "larger" in strategy["Skeletal Sacrifices"].mitigation.casefold()
    assert "Blue Meteors" in strategy
    assert "healing" in strategy["Blue Meteors"].mitigation.casefold()
    assert "Necrotic Cage" in strategy


def test_zelvraak_projection_has_reflections_realm_and_orb_assignments():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "zelvraak_the_unbreathing", "Zelvraak the Unbreathing"
    )

    assert {
        "Main Phase I",
        "Reflection Split I",
        "Afterlife / Realm Phase",
        "Post-Realm Colossus Phase",
        "Reflection Split II",
    } <= _labels(projection)
    assert {"75%", "50%", "25%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Sea Orb" in strategy
    assert "coverage" in strategy["Sea Orb"].mitigation.casefold()
    assert "Unbreakable Fear" in strategy
    assert "character" in strategy["Unbreakable Fear"].mitigation.casefold()
    assert "Sundered Soul" in strategy
    assert "golden ghost" in strategy["Sundered Soul"].mitigation.casefold()
