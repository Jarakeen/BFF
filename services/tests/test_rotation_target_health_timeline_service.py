import pytest

from services.rotation_target_health_timeline_service import (
    RotationTargetHealthObservation,
    RotationTargetHealthTimeline,
    RotationTargetHealthTimelineService,
)


def test_exact_observation_resolves_only_exact_time_without_validity_window() -> None:
    timeline = RotationTargetHealthTimeline(
        target_identity="boss",
        observations=(
            RotationTargetHealthObservation(
                time_seconds=42.0,
                target_identity="boss",
                current_health=240.0,
                maximum_health=1000.0,
                evidence="reviewed event",
            ),
        ),
    )
    resolver = RotationTargetHealthTimelineService().snapshot_resolver(timeline)

    exact = resolver(42.0)
    assert exact is not None
    assert exact.target("boss").health_fraction() == pytest.approx(0.24)
    assert resolver(42.1) is None


def test_explicit_validity_window_covers_only_declared_interval() -> None:
    timeline = RotationTargetHealthTimeline(
        target_identity="boss",
        observations=(
            RotationTargetHealthObservation(
                time_seconds=42.0,
                valid_until_seconds=44.0,
                target_identity="boss",
                current_health=240.0,
                maximum_health=1000.0,
            ),
        ),
    )
    resolver = RotationTargetHealthTimelineService().snapshot_resolver(timeline)

    assert resolver(43.0) is not None
    assert resolver(44.0) is not None
    assert resolver(44.01) is None


def test_overlapping_validity_windows_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        RotationTargetHealthTimeline(
            target_identity="boss",
            observations=(
                RotationTargetHealthObservation(
                    time_seconds=10.0,
                    valid_until_seconds=20.0,
                    target_identity="boss",
                    current_health=800.0,
                    maximum_health=1000.0,
                ),
                RotationTargetHealthObservation(
                    time_seconds=15.0,
                    target_identity="boss",
                    current_health=700.0,
                    maximum_health=1000.0,
                ),
            ),
        )


def test_target_identity_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="timeline target identity"):
        RotationTargetHealthTimeline(
            target_identity="boss",
            observations=(
                RotationTargetHealthObservation(
                    time_seconds=10.0,
                    target_identity="other",
                    current_health=800.0,
                    maximum_health=1000.0,
                ),
            ),
        )
