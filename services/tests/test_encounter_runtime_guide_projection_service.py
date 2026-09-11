from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.encounter_runtime_guide_projection_service import (
    EncounterRuntimeGuideProjectionService,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_projects_reviewed_lokkestiiz_runtime_notes() -> None:
    projection = EncounterRuntimeGuideProjectionService(REPO_ROOT / "data").get("lokkestiiz")

    assert projection.has_runtime_evidence is True
    assert projection.successful_kills == 10
    assert projection.reviewed_windows == 30
    assert len(projection.notes) == 5
    assert len(projection.role_guidance) == 4
    assert any(note.key == "flight_2_primary_sustained_pressure" for note in projection.notes)
    assert any(
        row.role == "healer" and "Flight 2" in row.guidance
        for row in projection.role_guidance
    )
    assert any(
        row.role == "damage_dealer" and "interrupt" in row.guidance.casefold()
        for row in projection.role_guidance
    )


def test_projection_keeps_runtime_evidence_separate_from_canonical_model() -> None:
    projection = EncounterRuntimeGuideProjectionService(REPO_ROOT / "data").get("lokkestiiz")

    assert projection.source_labels == (
        "ESO Logs reviewed Lokkestiiz successful-clear corpus",
    )
    assert all(note.confidence == "repeated_observation" for note in projection.notes)
    assert any("not universal fixed encounter constants" in row for row in projection.limitations)
    assert any("separate from canonical mechanics truth" in row for row in projection.limitations)


def test_returns_empty_projection_when_encounter_has_no_runtime_observation(tmp_path: Path) -> None:
    projection = EncounterRuntimeGuideProjectionService(tmp_path).get("xalvakka")

    assert projection.encounter_id == "xalvakka"
    assert projection.has_runtime_evidence is False
    assert projection.notes == ()
    assert projection.role_guidance == ()
    assert projection.successful_kills == 0
    assert projection.reviewed_windows == 0


def test_rejects_blank_encounter_id(tmp_path: Path) -> None:
    service = EncounterRuntimeGuideProjectionService(tmp_path)

    with pytest.raises(ValueError, match="encounter_id must be non-empty"):
        service.get("  ")
