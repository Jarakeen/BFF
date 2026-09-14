import pytest

from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterThresholdClockPoint,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon
from services.rotation_tank_encounter_transition_timing_service import (
    RotationTankEncounterTransitionTimingService,
)


def _projection(*, include_40=True):
    points = [
        EncounterThresholdClockPoint(
            fact_key="xalvakka_phase_thresholds",
            label="70 percent retreat",
            threshold_fraction=0.70,
            time_seconds=30.0,
            resolved=True,
            reason="projected",
        )
    ]
    if include_40:
        points.append(
            EncounterThresholdClockPoint(
                fact_key="xalvakka_phase_thresholds",
                label="40 percent retreat",
                threshold_fraction=0.40,
                time_seconds=60.0,
                resolved=True,
                reason="projected",
            )
        )
    return EncounterHealthThresholdProjection(
        encounter_id="xalvakka",
        difficulty="hardmode",
        maximum_health=100_000_000,
        trajectory=object(),  # timing service consumes the reviewed clock points only
        points=tuple(points),
        unresolved=(),
    )


def _horizon(encounter_id="xalvakka"):
    return RotationTankEncounterHorizon(
        encounter_id=encounter_id,
        end_seconds=100.0,
        resolved=True,
        evidence=("projected fight end",),
    )


def test_xalvakka_transition_projection_shifts_later_thresholds_and_fight_end():
    result = RotationTankEncounterTransitionTimingService().project(
        encounter_id="xalvakka",
        health_threshold_projection=_projection(),
        horizon=_horizon(),
    )

    assert result.resolved is True
    assert len(result.boundaries) == 2

    first, second = result.boundaries
    assert first.threshold_fraction == pytest.approx(0.70)
    assert first.crossing_time_seconds == pytest.approx(30.0)
    assert first.resume_time_seconds == pytest.approx(78.8095)
    assert first.sample_count == 4
    assert first.observed_min_delay_seconds == pytest.approx(44.437)
    assert first.observed_max_delay_seconds == pytest.approx(65.064)

    assert second.threshold_fraction == pytest.approx(0.40)
    assert second.crossing_time_seconds == pytest.approx(108.8095)
    assert second.resume_time_seconds == pytest.approx(173.3705)
    assert second.sample_count == 3

    assert result.adjusted_end_seconds == pytest.approx(213.3705)
    assert result.crossing_time_for(0.40) == pytest.approx(108.8095)
    assert result.resume_time_for(0.40) == pytest.approx(173.3705)
    assert any("samples=4" in row for row in result.evidence)
    assert any("XVMgLdq6GpQ7bhKN" in row for row in result.evidence)


def test_encounter_without_reviewed_transition_timing_keeps_canonical_horizon():
    result = RotationTankEncounterTransitionTimingService().project(
        encounter_id="taleria_hm",
        health_threshold_projection=None,
        horizon=_horizon(encounter_id="taleria_hm"),
    )

    assert result.resolved is True
    assert result.boundaries == ()
    assert result.adjusted_end_seconds == pytest.approx(100.0)


def test_reviewed_transition_projection_fails_closed_when_required_threshold_is_missing():
    result = RotationTankEncounterTransitionTimingService().project(
        encounter_id="xalvakka",
        health_threshold_projection=_projection(include_40=False),
        horizon=_horizon(),
    )

    assert result.resolved is False
    assert result.adjusted_end_seconds is None
    assert len(result.boundaries) == 1
    assert "no canonical 40% health-threshold clock point" in result.unresolved[0]
