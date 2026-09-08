import json

import pytest

from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)


def _write(tmp_path, payload):
    path = tmp_path / "observations.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_candidate_fixture_is_rejected_before_runtime_promotion(tmp_path):
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "review_status": "candidate",
            "game_version": "U50",
            "samples": [],
        },
    )

    with pytest.raises(ValueError, match="is not reviewed"):
        RotationHealerPeriodicObservationFixtureService(tmp_path / "missing.db").load(path)


def test_explicit_reviewed_fixture_is_accepted(tmp_path):
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "review_status": "reviewed",
            "game_version": "U50",
            "samples": [],
        },
    )

    report = RotationHealerPeriodicObservationFixtureService(tmp_path / "missing.db").load(path)

    assert report.entries == ()
    assert report.unresolved == ()


def test_legacy_schema_v1_fixture_without_review_status_remains_accepted(tmp_path):
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "game_version": "U50",
            "samples": [],
        },
    )

    report = RotationHealerPeriodicObservationFixtureService(tmp_path / "missing.db").load(path)

    assert report.entries == ()
