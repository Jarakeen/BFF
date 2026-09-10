from types import SimpleNamespace

from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.runtime_healer_wait_decision_provider import RuntimeHealerWaitDecisionProvider
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationService,
)


def _skill(time_seconds: float, name: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _ro_incentive() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified synthetic RO assignment evidence",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
    )


def _seed_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Synthetic Warden",
        build_name="RoJo Healer",
        duration_seconds=31.0,
        actions=(
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(3.0, "Action A"),
            _skill(24.0, "Long Buff"),
            _skill(26.0, "Long Buff"),
            _skill(28.0, "Long Buff"),
            _skill(29.0, "Action B"),
            _skill(30.0, "Action C"),
            _skill(31.0, "Action D"),
        ),
    )


def _rules() -> tuple[RotationRecastRule, ...]:
    return (
        RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),
        RotationRecastRule("Action A", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action B", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action C", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action D", duration_seconds=60.0, bar="front"),
    )


class _NoPressureReplayService:
    """Stable sustain fixture: recovery pressure is never the reason to heavy."""

    @staticmethod
    def replay(*, build, plan, resource, restoration_resolver, **kwargs):
        timeline = SimpleNamespace(
            resource=resource,
            starting_amount=30_000,
            ending_amount=30_000,
            events=(),
            total_shortfall=0,
        )
        projection = SimpleNamespace(run=SimpleNamespace(timeline=timeline))
        return SimpleNamespace(
            initial_projection=projection,
            final_projection=projection,
            restoration_events=(),
            steps=(),
        )

    @staticmethod
    def pressure_resolver(**kwargs):
        return lambda context: None


def test_ro_required_heavies_survive_fixed_point_without_recovery_pressure() -> None:
    seed = _seed_plan()
    rules = _rules()
    incentive = _ro_incentive()

    def generate(pressure_resolver):
        provider = RuntimeHealerWaitDecisionProvider(
            incentives=(incentive,),
            required_window_seconds=1.8,
            recovery_pressure_resolver=pressure_resolver,
        )
        return DurationAwareRotationScheduler().refine(
            seed,
            rules,
            wait_decision=provider,
        )

    result = RotationRecoveryHeavyStabilizationService(
        replay_service=_NoPressureReplayService()
    ).stabilize(
        build=PlayerBuild(Name="Synthetic Warden", BuildName="RoJo Healer"),
        generate=generate,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.5,
        restoration_resolver=lambda action: None,
        max_iterations=4,
    )

    assert result.converged is True
    assert result.termination_reason == "stable_fixed_point"
    assert result.tracked_hard_obligations_satisfied is True
    assert len(result.iterations) == 2

    heavies = tuple(
        float(action.time_seconds)
        for action in result.plan.actions
        if action.kind is RotationActionKind.HEAVY_ATTACK
    )
    assert heavies == (2.0, 28.0)
    expected_signature = (
        (2.0, 0, "front", "Heavy Attack"),
        (28.0, 0, "front", "Heavy Attack"),
    )
    assert all(
        iteration.heavy_signature == expected_signature
        for iteration in result.iterations
    )
