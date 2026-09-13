import pytest

from services.rotation_detonating_siphon_controlled_spatial_evidence_service import (
    RotationDetonatingSiphonControlledSpatialEvidenceService,
    RotationDetonatingSiphonControlledSpatialSample,
)


def sample(label, *, caster, corpse, target, hit):
    return RotationDetonatingSiphonControlledSpatialSample(
        label=label,
        caster=caster,
        corpse_candidate=corpse,
        target=target,
        damage_observed=hit,
    )


def test_empty_samples_fail_closed() -> None:
    report = RotationDetonatingSiphonControlledSpatialEvidenceService().analyze(())
    assert report.sample_count == 0
    assert report.unresolved
    assert report.corridor_width_resolved is False


def test_circle_hypotheses_are_compared_independently() -> None:
    report = RotationDetonatingSiphonControlledSpatialEvidenceService().analyze(
        (
            sample(
                "caster-only-hit",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(2.0, 0.0),
                hit=True,
            ),
            sample(
                "corpse-only-miss",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(18.0, 0.0),
                hit=False,
            ),
        )
    )

    assert report.caster_circle.consistent is True
    assert report.caster_circle.matching_samples == 2
    assert report.corpse_circle.consistent is False
    assert set(report.corpse_circle.conflicting_samples) == {
        "caster-only-hit",
        "corpse-only-miss",
    }


def test_corridor_bounds_use_hit_and_interior_no_hit_samples() -> None:
    report = RotationDetonatingSiphonControlledSpatialEvidenceService().analyze(
        (
            sample(
                "corridor-hit",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(10.0, 1.5),
                hit=True,
            ),
            sample(
                "corridor-miss",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(10.0, 3.0),
                hit=False,
            ),
        )
    )

    assert report.hit_sample_minimum_segment_half_width == pytest.approx(1.5)
    assert report.no_hit_segment_upper_bound == pytest.approx(3.0)
    assert report.corridor_width_resolved is True
    assert report.unresolved == ()


def test_endpoint_no_hit_does_not_bound_corridor_width() -> None:
    report = RotationDetonatingSiphonControlledSpatialEvidenceService().analyze(
        (
            sample(
                "interior-hit",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(10.0, 1.0),
                hit=True,
            ),
            sample(
                "past-end-miss",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(25.0, 1.0),
                hit=False,
            ),
        )
    )

    assert report.hit_sample_minimum_segment_half_width == pytest.approx(1.0)
    assert report.no_hit_segment_upper_bound is None
    assert report.corridor_width_resolved is False
    assert any("no interior-segment no-hit" in item for item in report.unresolved)


def test_conflicting_corridor_bounds_remain_unresolved() -> None:
    report = RotationDetonatingSiphonControlledSpatialEvidenceService().analyze(
        (
            sample(
                "wide-hit",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(10.0, 4.0),
                hit=True,
            ),
            sample(
                "narrow-miss",
                caster=(0.0, 0.0),
                corpse=(20.0, 0.0),
                target=(10.0, 3.0),
                hit=False,
            ),
        )
    )

    assert report.corridor_width_resolved is False
    assert any("do not define a non-overlapping" in item for item in report.unresolved)
