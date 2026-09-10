import json

import pytest

from services.rotation_healer_periodic_observation_review_service import (
    RotationHealerPeriodicObservationReviewService,
)


def _candidate(tmp_path, *, status="candidate", samples=None):
    payload = {
        "schema_version": 1,
        "review_status": status,
        "game_version": "U50",
        "source": {
            "kind": "esologs_raw_export",
            "path": "raw.json",
            "report_code": "ABC123",
            "fight_id": 7,
            "caster_id": 42,
            "timestamp_unit": "milliseconds",
        },
        "samples": samples
        if samples is not None
        else [
            {
                "source_name": "Budding Seeds",
                "coefficient_number": 2,
                "activation_time_seconds": 10.0,
                "observed_tick_times_seconds": [11.0, 12.0, 13.0],
                "observation_end_seconds": 16.02,
                "provenance": ["candidate extracted from ESO Logs"],
                "candidate_metadata": {"ability_game_id": 93807},
            },
            {
                "source_name": "Energy Orb",
                "coefficient_number": 1,
                "activation_time_seconds": 20.0,
                "observed_tick_times_seconds": [21.0, 22.0],
                "observation_end_seconds": 30.02,
                "provenance": ["candidate extracted from ESO Logs"],
                "candidate_metadata": {"ability_game_id": 43447},
            },
        ],
    }
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_promotes_only_explicitly_approved_samples_and_preserves_source(tmp_path):
    path, candidate = _candidate(tmp_path)

    result = RotationHealerPeriodicObservationReviewService().promote(
        path,
        approved_sample_indices=(2,),
        review_note="paired cast and periodic events reviewed against raw report",
        reviewed_by="tester",
        reviewed_at="2026-09-10T21:30:00Z",
    )

    payload = result.reviewed_payload
    assert payload["review_status"] == "reviewed"
    assert payload["source"] == candidate["source"]
    assert payload["samples"] == [candidate["samples"][1]]
    assert payload["review"]["approved_sample_indices"] == [2]
    assert payload["review"]["review_note"].startswith("paired cast")
    assert payload["review"]["reviewed_by"] == "tester"


def test_candidate_file_is_not_mutated_during_promotion(tmp_path):
    path, candidate = _candidate(tmp_path)

    result = RotationHealerPeriodicObservationReviewService().promote(
        path,
        approved_sample_indices=(1,),
        review_note="reviewed sample one",
        reviewed_at="2026-09-10T21:30:00Z",
    )

    assert json.loads(path.read_text(encoding="utf-8")) == candidate
    output = tmp_path / "reviewed.json"
    RotationHealerPeriodicObservationReviewService.write(result, output)
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["review_status"] == "reviewed"
    assert written["samples"][0]["source_name"] == "Budding Seeds"


def test_promotion_rejects_implicit_or_invalid_approval(tmp_path):
    path, _ = _candidate(tmp_path)
    service = RotationHealerPeriodicObservationReviewService()

    with pytest.raises(ValueError, match="at least one reviewed sample index"):
        service.promote(path, approved_sample_indices=(), review_note="reviewed")
    with pytest.raises(ValueError, match="must be unique"):
        service.promote(path, approved_sample_indices=(1, 1), review_note="reviewed")
    with pytest.raises(ValueError, match="between 1 and 2"):
        service.promote(path, approved_sample_indices=(3,), review_note="reviewed")
    with pytest.raises(ValueError, match="requires a review note"):
        service.promote(path, approved_sample_indices=(1,), review_note="")


def test_promotion_rejects_non_candidate_and_unreviewable_samples(tmp_path):
    reviewed_path, _ = _candidate(tmp_path, status="reviewed")
    with pytest.raises(ValueError, match="requires review_status='candidate'"):
        RotationHealerPeriodicObservationReviewService().promote(
            reviewed_path,
            approved_sample_indices=(1,),
            review_note="reviewed",
        )

    bad_path, _ = _candidate(
        tmp_path,
        samples=[
            {
                "source_name": "Budding Seeds",
                "coefficient_number": 2,
                "activation_time_seconds": 10.0,
                "observed_tick_times_seconds": [],
                "observation_end_seconds": 16.0,
                "provenance": ["raw"],
            }
        ],
    )
    with pytest.raises(ValueError, match="requires tick timestamps"):
        RotationHealerPeriodicObservationReviewService().promote(
            bad_path,
            approved_sample_indices=(1,),
            review_note="reviewed",
        )
