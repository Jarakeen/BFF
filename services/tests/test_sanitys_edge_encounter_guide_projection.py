from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _markers(projection):
    return {row.marker for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_yaseyla_projection_has_threshold_timeline_and_raid_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "exarchanic_yaseyla", "Exarchanic Yaseyla"
    )

    assert {"90%", "70%", "60%", "50%", "35%", "30%", "20%", "10%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Frost Bomb" in strategy
    assert "8-second" in strategy["Frost Bomb"].mitigation
    assert "Wamasu Charge" in strategy
    assert "clear the lane" in strategy["Wamasu Charge"].mitigation
    assert "True Shot" in strategy
    assert "Interrupt" in strategy["True Shot"].mitigation


def test_twelvane_projection_has_control_pathway_and_chimera_phases():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "archwizard_twelvane", "Archwizard Twelvane"
    )

    labels = {row.label for row in projection.timeline}
    assert {"Archwizard Twelvane", "Control Pathways", "Chimera"} <= labels
    strategy = _strategy(projection)
    assert "Radiance" in strategy
    assert "15 seconds" in strategy["Radiance"].mitigation
    assert "Chain Circuit" in strategy
    assert "30-second Circuit Charge" in strategy["Chain Circuit"].mitigation
    assert "Inferno" in strategy
    assert "Sizzling Crater" in strategy["Inferno"].mitigation


def test_ansuul_projection_has_thresholds_and_current_torment_timeout():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "ansuul_the_tormentor", "Ansuul the Tormentor"
    )

    assert {"90%", "80%", "70%", "60%", "50%", "40%", "30%", "20%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Manic Phobia" in strategy
    assert "Essence Manifestation" in strategy["Manic Phobia"].mitigation
    assert "The Ritual" in strategy
    assert "portal team" in strategy["The Ritual"].mitigation
    assert "Vanton Torment Timeout" in strategy
    assert "3 minutes" in strategy["Vanton Torment Timeout"].mitigation
    assert "Neural Takeover" in strategy["Vanton Torment Timeout"].mitigation
