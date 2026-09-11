from engine.config import get_data_dir
from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


def _projection(encounter_id: str, encounter_name: str):
    return EncounterGuideEvidenceProjectionService(get_data_dir()).get(
        encounter_id, encounter_name
    )


def test_lokkestiiz_reviewed_guide_projects_flight_thresholds_and_handling():
    projection = _projection("lokkestiiz", "Lokkestiiz")

    markers = tuple(row.marker for row in projection.timeline)
    mechanics = {row.mechanic: row for row in projection.strategy}

    assert markers == ("80%", "50%", "20%")
    assert "Icy Winds" in mechanics
    assert "8 seconds" in mechanics["Icy Winds"].mitigation
    assert "Ice Laser Beam" in mechanics
    assert "Block" in mechanics["Ice Laser Beam"].mitigation


def test_yolnahkriin_reviewed_guide_projects_fire_phase_thresholds_and_handling():
    projection = _projection("yolnahkriin", "Yolnahkriin")

    markers = tuple(row.marker for row in projection.timeline)
    mechanics = {row.mechanic: row for row in projection.strategy}

    assert markers == ("75%", "50%", "25%")
    assert "Fire Geyser / Explosion" in mechanics
    assert "assigned stack" in mechanics["Fire Geyser / Explosion"].mitigation
    assert "Iron Atronach" in mechanics
    assert "Back tank" in mechanics["Iron Atronach"].mitigation


def test_nahviintaas_reviewed_guide_projects_portals_adds_execute_and_handling():
    projection = _projection("nahviintaas", "Nahviintaas")

    markers = tuple(row.marker for row in projection.timeline)
    mechanics = {row.mechanic: row for row in projection.strategy}

    assert set(markers) == {"90%", "80%", "70%", "60%", "50%", "40%", "31%"}
    assert "Eternal Servant" in mechanics
    assert "90-second timeout" in mechanics["Eternal Servant"].mitigation
    assert "Marked for Death" in mechanics
    assert "Tank swap" in mechanics["Marked for Death"].mitigation
