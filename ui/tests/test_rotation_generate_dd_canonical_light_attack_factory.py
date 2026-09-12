from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationWeaponAttackBuildEvaluationResolution,
)
import ui.rotation_generate_dd_role_evidence_support as dd_support


class _StaticContext:
    def __init__(self):
        self.front = SimpleNamespace(active_bar="front")
        self.back = SimpleNamespace(active_bar="back")

    def context_for(self, bar):
        return {"front": self.front, "back": self.back}.get(bar)


class _EvaluationService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _FakeLightAttackService:
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.calls.append(kwargs)

    def evaluate_action(self, *, candidate, action):
        evaluation = self.kwargs["evaluation"]
        value = 100.0 if evaluation == "front-eval" else 200.0
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=value,
        )


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="bars",
        plan=RotationPlan(
            character_name="Parse Cat",
            build_name="DD",
            duration_seconds=10.0,
            actions=(
                RotationAction(1.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
                RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
                RotationAction(5.0, 1, RotationActionKind.LIGHT_ATTACK, bar="back"),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_factory_routes_light_attacks_through_bar_specific_build_evaluations(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "RotationCandidateLightAttackDamageEvidenceService",
        _FakeLightAttackService,
    )
    _FakeLightAttackService.calls.clear()
    resolution = RotationWeaponAttackBuildEvaluationResolution(
        build=object(),  # type: ignore[arg-type]
        evaluations=(("front", "front-eval"), ("back", "back-eval")),  # type: ignore[arg-type]
        unresolved=(),
    )
    evaluation_service = _EvaluationService(resolution)
    factory = dd_support.RotationGenerateDDCanonicalWeaponAttackProviderFactory(
        database_path="unused.db",
        evaluation_service=evaluation_service,  # type: ignore[arg-type]
    )
    static = _StaticContext()
    build = object()

    light, heavy = factory.providers_for(
        player_build=build,  # type: ignore[arg-type]
        static_context=static,
        target_resistance=18200.0,
    )

    assert heavy is None
    assert light is not None
    candidate = _candidate()
    front = light.evaluate_action(candidate=candidate, action=candidate.plan.actions[0])
    back = light.evaluate_action(candidate=candidate, action=candidate.plan.actions[2])

    assert front.unresolved == ()
    assert front.damage_value == pytest.approx(100.0)
    assert back.unresolved == ()
    assert back.damage_value == pytest.approx(200.0)
    assert evaluation_service.calls == [
        {"player_build": build, "static_context": static}
    ]
    assert [call["evaluation"] for call in _FakeLightAttackService.calls] == [
        "front-eval",
        "back-eval",
    ]
    assert all(
        call["evaluation_context"].target_resistance == 18200.0
        for call in _FakeLightAttackService.calls
    )


def test_factory_preserves_bridge_failure_as_light_attack_unresolved() -> None:
    resolution = RotationWeaponAttackBuildEvaluationResolution(
        build=None,
        evaluations=(),
        unresolved=("canonical weapon adaptation unresolved",),
    )
    factory = dd_support.RotationGenerateDDCanonicalWeaponAttackProviderFactory(
        database_path="unused.db",
        evaluation_service=_EvaluationService(resolution),  # type: ignore[arg-type]
    )
    light, heavy = factory.providers_for(
        player_build=object(),  # type: ignore[arg-type]
        static_context=_StaticContext(),
        target_resistance=18200.0,
    )

    assert heavy is None
    assert light is not None
    action = RotationAction(1.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    evidence = light.evaluate_action(candidate=_candidate(), action=action)
    assert evidence.damage_value is None
    assert evidence.unresolved == ("canonical weapon adaptation unresolved",)
