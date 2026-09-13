from __future__ import annotations

from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


def test_unnerving_boneyard_reviews_cast_anchor_but_remains_non_executable() -> None:
    entry = RotationDDPeriodicRuntimeSemanticsReviewService().by_component()[
        ("unnerving_boneyard", 1)
    ]

    assert entry.duration_seconds == 10.0
    assert entry.activation_anchor == "cast"
    assert entry.reviewed_interval_seconds is None
    assert entry.first_tick_offset_seconds is None
    assert entry.refresh_boundary is None
    assert entry.magnitude_policy is None
    assert entry.executable_complete is False
    assert entry.unresolved_executable_fields == (
        "reviewed_interval_seconds",
        "first_tick_offset_seconds",
        "refresh_boundary",
        "magnitude_policy",
    )


def test_unnerving_boneyard_review_records_current_and_corpus_anchor_evidence() -> None:
    entry = RotationDDPeriodicRuntimeSemanticsReviewService().by_component()[
        ("unnerving_boneyard", 1)
    ]
    text = "\n".join(entry.evidence)

    assert "ground-targeted 10-second field" in text
    assert "1870 events were cast-track linked" in text
    assert "activation anchor is therefore reviewed as cast/placement" in text
    assert "cadence, first-tick offset, refresh policy, and magnitude policy remain" in text
