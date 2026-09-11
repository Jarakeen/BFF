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


def test_rogerain_projection_has_goat_and_gate_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("rogerain_the_sly", "Rogerain the Sly")
    assert "Main / Chaos Cycle" in _labels(projection)
    strategy = _strategy(projection)
    assert "Goatification" in strategy
    assert "sweetroll" in strategy["Goatification"].mitigation.casefold()
    assert "Chaos Gate" in strategy
    assert "portal" in strategy["Chaos Gate"].mitigation.casefold()


def test_artifact_bearers_projection_tracks_all_three_members_and_return_phase():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("artifact_bearers", "Artifact Bearers")
    assert {"Eliam Opening", "Liramindrel Joins", "Ihudir Joins", "Both Allies Return"} <= _labels(projection)
    assert {"~80%", "~50%", "~30%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Liramindrel Arrow Traps" in strategy
    assert "stun" in strategy["Liramindrel Arrow Traps"].mitigation.casefold()
    assert "Ihudir Interrupt" in strategy


def test_prior_thierric_projection_has_duplicate_and_interrupt_checks():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("prior_thierric_sarazen", "Prior Thierric Sarazen")
    assert "Main / Duplicate Pressure" in _labels(projection)
    strategy = _strategy(projection)
    assert "Duplicate Wall" in strategy
    assert "safe gap" in strategy["Duplicate Wall"].mitigation.casefold()
    assert "Opalescent Impale" in strategy
    assert "interrupt" in strategy["Opalescent Impale"].mitigation.casefold()


def test_scorion_broodlord_projection_has_stone_and_add_priority():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("scorion_broodlord", "Scorion Broodlord")
    assert "Add / Agonymium Cycle" in _labels(projection)
    strategy = _strategy(projection)
    assert "Agonymium Stone" in strategy
    assert "heals" in strategy["Agonymium Stone"].mitigation.casefold()
    assert "Hard Mode Add Priority" in strategy
    assert "interrupt" in strategy["Hard Mode Add Priority"].mitigation.casefold()


def test_cyronin_projection_has_mobile_wave_and_hardmode_orb_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("cyronin_artellian", "Cyronin Artellian")
    assert "Main / Mobile Add Pressure" in _labels(projection)
    strategy = _strategy(projection)
    assert "Dread Surge" in strategy
    assert "dodge" in strategy["Dread Surge"].mitigation.casefold()
    assert "Hard Mode Lightning Orbs" in strategy
    assert "away from the group" in strategy["Hard Mode Lightning Orbs"].mitigation.casefold()


def test_magma_incarnate_projection_has_portals_and_hardmode_scorion_thresholds():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("magma_incarnate", "Magma Incarnate")
    assert {"Main / Portal Cycle", "Hard Mode Scorion I", "Hard Mode Scorion II"} <= _labels(projection)
    assert {"~60%", "~30%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Portal / Agonymium Stone" in strategy
    assert "invulnerable" in strategy["Portal / Agonymium Stone"].mitigation.casefold()
    assert "Incarnate Outburst" in strategy
    assert "tank" in strategy["Incarnate Outburst"].mitigation.casefold()
