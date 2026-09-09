from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_lokkestiiz_horn_readiness_service import (
    RotationLokkestiizHornReadinessService,
)
from services.rotation_lokkestiiz_landing_clock_service import LokkestiizLandingClockEvidence


def _plan(*, duration: float, attack_times: tuple[float, ...]) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=duration,
        actions=tuple(
            RotationAction(
                time_seconds=time,
                sequence=index,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="back",
            )
            for index, time in enumerate(attack_times)
        ),
    )


def _clocks(*times: float, unresolved: tuple[str, ...] = ()) -> LokkestiizLandingClockEvidence:
    return LokkestiizLandingClockEvidence(
        landing_times_seconds=tuple(times),
        sources=tuple("observed pull" for _ in times),
        unresolved=unresolved,
    )


def test_horn_readiness_spends_one_cost_at_each_landing_and_carries_balance() -> None:
    plan = _plan(
        duration=90.0,
        attack_times=tuple(float(value) for value in range(0, 89, 8)),
    )

    result = RotationLokkestiizHornReadinessService().evaluate(
        plan=plan,
        landing_clocks=_clocks(10.0, 50.0, 90.0),
        starting_amount=500.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    assert result.ready is True
    assert [item.affordable for item in result.landings] == [True, True, True]
    assert result.landings[0].amount_before_spend >= 250.0
    assert result.landings[0].amount_after_spend == result.landings[0].amount_before_spend - 250.0
    assert result.landings[1].amount_after_spend == result.landings[1].amount_before_spend - 250.0
    assert result.landings[2].amount_after_spend == result.landings[2].amount_before_spend - 250.0


def test_horn_readiness_rejects_candidate_that_cannot_afford_later_landing() -> None:
    plan = _plan(
        duration=30.0,
        attack_times=(0.0, 8.0, 16.0, 24.0),
    )

    result = RotationLokkestiizHornReadinessService().evaluate(
        plan=plan,
        landing_clocks=_clocks(10.0, 20.0, 30.0),
        starting_amount=500.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    assert result.ready is False
    assert [item.affordable for item in result.landings] == [True, True, False]
    assert any("landing 3" in item for item in result.unresolved)
    assert any("required=250.000" in item for item in result.unresolved)


def test_horn_readiness_requires_explicit_attack_success_evidence() -> None:
    result = RotationLokkestiizHornReadinessService().evaluate(
        plan=_plan(duration=20.0, attack_times=(0.0, 8.0, 16.0)),
        landing_clocks=_clocks(10.0, 15.0, 20.0),
        starting_amount=500.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=False,
    )

    assert result.ready is False
    assert result.generation_event_count == 0
    assert any("not proven successful damaging combat triggers" in item for item in result.unresolved)


def test_horn_readiness_refuses_plan_that_ends_before_final_landing() -> None:
    result = RotationLokkestiizHornReadinessService().evaluate(
        plan=_plan(duration=25.0, attack_times=(0.0, 8.0, 16.0, 24.0)),
        landing_clocks=_clocks(10.0, 20.0, 30.0),
        starting_amount=500.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    assert result.ready is False
    assert result.landings == ()
    assert any("does not extend through the final observed" in item for item in result.unresolved)


def test_horn_readiness_preserves_unresolved_clock_evidence() -> None:
    result = RotationLokkestiizHornReadinessService().evaluate(
        plan=_plan(duration=30.0, attack_times=(0.0, 8.0, 16.0, 24.0)),
        landing_clocks=_clocks(
            10.0,
            20.0,
            30.0,
            unresolved=("clock source is incomplete",),
        ),
        starting_amount=500.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    assert result.ready is False
    assert "clock source is incomplete" in result.unresolved
