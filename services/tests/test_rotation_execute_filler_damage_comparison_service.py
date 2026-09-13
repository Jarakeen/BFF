from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_damage_comparison_service import (
    RotationExecuteFillerDamageComparisonService,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
)


class _DamageProvider:
    def __init__(self, values):
        self.values = dict(values)
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append(action)
        value = self.values.get(action.name)
        if isinstance(value, tuple):
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=value,
            )
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=value,
        )


def _candidate():
    plan = RotationPlan(
        character_name="Tester",
        build_name="DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=8.0,
                sequence=2,
                kind=RotationActionKind.SKILL,
                name="Filler",
                bar="front",
            ),
        ),
    )
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )


def _opportunity():
    return RotationExecuteFillerOpportunity(
        time_seconds=8.0,
        bar="front",
        current_skill_name="Filler",
        execute_skill_name="Execute",
        current_priority=1,
        execute_priority=5,
        target_identity="boss",
        active_thresholds=(0.25,),
    )


def test_execute_replacement_requires_strict_damage_gain() -> None:
    provider = _DamageProvider({"Filler": 1000.0, "Execute": 1500.0})
    result = RotationExecuteFillerDamageComparisonService(
        action_damage_provider=provider,
    ).compare(candidate=_candidate(), opportunity=_opportunity())

    assert result.current_damage == 1000.0
    assert result.execute_damage == 1500.0
    assert result.replace_with_execute is True
    assert result.unresolved == ()
    assert provider.calls[1].name == "Execute"
    assert provider.calls[1].time_seconds == 8.0
    assert provider.calls[1].sequence == 2
    assert provider.calls[1].bar == "front"


def test_equal_or_lower_execute_damage_does_not_replace() -> None:
    equal = RotationExecuteFillerDamageComparisonService(
        action_damage_provider=_DamageProvider({"Filler": 1000.0, "Execute": 1000.0}),
    ).compare(candidate=_candidate(), opportunity=_opportunity())
    lower = RotationExecuteFillerDamageComparisonService(
        action_damage_provider=_DamageProvider({"Filler": 1000.0, "Execute": 900.0}),
    ).compare(candidate=_candidate(), opportunity=_opportunity())

    assert equal.replace_with_execute is False
    assert lower.replace_with_execute is False


def test_unresolved_execute_damage_fails_closed() -> None:
    result = RotationExecuteFillerDamageComparisonService(
        action_damage_provider=_DamageProvider(
            {"Filler": 1000.0, "Execute": ("execute interpolation unresolved",)}
        ),
    ).compare(candidate=_candidate(), opportunity=_opportunity())

    assert result.replace_with_execute is False
    assert result.execute_damage is None
    assert result.unresolved == (
        "execute 'Execute': execute interpolation unresolved",
    )


def test_missing_exact_filler_action_fails_closed() -> None:
    opportunity = RotationExecuteFillerOpportunity(
        time_seconds=9.0,
        bar="front",
        current_skill_name="Filler",
        execute_skill_name="Execute",
        current_priority=1,
        execute_priority=5,
        target_identity="boss",
        active_thresholds=(0.25,),
    )
    result = RotationExecuteFillerDamageComparisonService(
        action_damage_provider=_DamageProvider({"Filler": 1000.0, "Execute": 1500.0}),
    ).compare(candidate=_candidate(), opportunity=opportunity)

    assert result.replace_with_execute is False
    assert "found 0" in result.unresolved[0]
