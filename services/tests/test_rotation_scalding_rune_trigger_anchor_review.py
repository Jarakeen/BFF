from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


def test_scalding_rune_review_promotes_only_trigger_activation_anchor() -> None:
    rows = RotationDDPeriodicRuntimeSemanticsReviewService().by_component()

    entry = rows[("scalding_rune", 2)]

    assert entry.duration_seconds == 22.0
    assert entry.activation_anchor == "trigger"
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
