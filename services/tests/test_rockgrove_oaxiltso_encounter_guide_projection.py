from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def test_oaxiltso_reviewed_timeline_surfaces_spawn_thresholds_and_conflict_note():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("oaxiltso", "Oaxiltso")

    markers = tuple(row.marker for row in projection.timeline)
    assert markers == ("95%", "75%", "50%", "25%")
    assert all(row.label == "Havocrel Annihilator Spawn" for row in projection.timeline)
    assert "90% instead of 95%" in projection.timeline[0].detail


def test_oaxiltso_existing_strategy_remains_available_with_timeline_fallback():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("oaxiltso", "Oaxiltso")

    mechanic_names = {row.mechanic for row in projection.strategy}
    assert "Noxious Sludge" in mechanic_names
    assert "Savage Blitz" in mechanic_names
    assert "Fiery Stomp" in mechanic_names
    assert projection.timeline
