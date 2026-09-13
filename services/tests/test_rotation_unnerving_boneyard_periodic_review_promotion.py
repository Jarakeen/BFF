from __future__ import annotations

from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


def test_unnerving_boneyard_reviews_cast_anchor_refresh_and_cadence_but_remains_non_executable() -> None:
    entry = RotationDDPeriodicRuntimeSemanticsReviewService().by_component()[
        ("unnerving_boneyard", 1)
    ]

    assert entry.duration_seconds == 10.0
    assert entry.activation_anchor == "cast"
    assert entry.reviewed_interval_seconds == 1.0
    assert entry.first_tick_offset_seconds is None
    assert entry.refresh_boundary == "replace_before_recast_tick"
    assert entry.magnitude_policy is None
    assert entry.executable_complete is False
    assert entry.unresolved_executable_fields == (
        "first_tick_offset_seconds",
        "magnitude_policy",
    )


def test_unnerving_boneyard_review_records_current_anchor_refresh_and_cadence_evidence() -> None:
    entry = RotationDDPeriodicRuntimeSemanticsReviewService().by_component()[
        ("unnerving_boneyard", 1)
    ]
    text = "\n".join(entry.evidence)

    assert "ground-targeted 10-second field" in text
    assert "1870 events were cast-track linked" in text
    assert "activation anchor is therefore reviewed as cast/placement" in text
    assert "141 consecutive cast pairs" in text
    assert "1 ms after the cast" in text
    assert "replace the old instance before any recast-boundary tick" in text
    assert "1226 adjacent intervals" in text
    assert "96.3%" in text
    assert "reviewed recurrence cadence is therefore 1.0 second" in text
    assert "P90 was 3.3282 seconds" in text
    assert "exact first-tick offset and magnitude policy remain" in text
