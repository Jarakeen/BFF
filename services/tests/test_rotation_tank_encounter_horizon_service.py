from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
)
from services.rotation_tank_encounter_horizon_service import (
    RotationTankEncounterHorizonService,
)
from minmax.fight_damage_trajectory import (
    RaidDamageSegment,
    project_health_threshold_times,
)


def _projection(*, encounter_id: str = "xalvakka", end_seconds: float | None = None):
    trajectory = project_health_threshold_times(
        maximum_health=100_000_000.0,
        thresholds=(0.70,),
        segments=(RaidDamageSegment(0.0, end_seconds, 2_000_000.0),),
    )
    return EncounterHealthThresholdProjection(
        encounter_id=encounter_id,
        difficulty="hardmode",
        maximum_health=100_000_000,
        trajectory=trajectory,
        points=(),
        unresolved=(),
    )


def test_tank_horizon_uses_canonical_projected_fight_end() -> None:
    result = RotationTankEncounterHorizonService().resolve(
        encounter_id="xalvakka",
        health_threshold_projection=_projection(),
    )

    assert result.resolved is True
    assert result.end_seconds == 50.0
    assert result.unresolved == ()
    assert any("maximum_health=100000000" in item for item in result.evidence)


def test_tank_horizon_fails_closed_when_damage_evidence_does_not_reach_kill() -> None:
    result = RotationTankEncounterHorizonService().resolve(
        encounter_id="xalvakka",
        health_threshold_projection=_projection(end_seconds=20.0),
    )

    assert result.resolved is False
    assert result.end_seconds is None
    assert any("before encounter Health reaches zero" in item for item in result.unresolved)


def test_tank_horizon_fails_closed_without_canonical_projection() -> None:
    result = RotationTankEncounterHorizonService().resolve(
        encounter_id="xalvakka",
        health_threshold_projection=None,
    )

    assert result.resolved is False
    assert result.end_seconds is None
    assert result.unresolved


def test_tank_horizon_rejects_projection_from_other_encounter() -> None:
    try:
        RotationTankEncounterHorizonService().resolve(
            encounter_id="xalvakka",
            health_threshold_projection=_projection(encounter_id="taleria_hm"),
        )
    except ValueError as exc:
        assert "does not match selected encounter" in str(exc)
    else:
        raise AssertionError("foreign encounter projection should fail closed")
