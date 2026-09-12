from types import SimpleNamespace

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

    def resolve(self, **kwargs):
        return self.result


class _FakeHeavyAttackService:
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.calls.append(kwargs)

    def evaluate_action(self, *, candidate, action):
        evidence = self.kwargs["completion_evidence"]
        if not evidence:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=("missing verified heavy completion",),
            )
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=500.0,
        )


def _candidate(*, reserved: bool) -> GeneratedRotationCandidate:
    unresolved = ()
    if reserved:
        unresolved = (
            "caller-proven heavy_attack at 1.000s reserved the front-bar timeline through 2.800s",
        )
    return GeneratedRotationCandidate(
        candidate_id="heavy-dd",
        plan=RotationPlan(
            character_name="Parse Cat",
            build_name="DD",
            duration_seconds=10.0,
            actions=(
                RotationAction(
                    1.0,
                    0,
                    RotationActionKind.HEAVY_ATTACK,
                    bar="front",
                ),
            ),
            unresolved=unresolved,
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _factory(monkeypatch):
    monkeypatch.setattr(
        dd_support,
        "RotationCandidateHeavyAttackDamageEvidenceService",
        _FakeHeavyAttackService,
    )
    _FakeHeavyAttackService.calls.clear()
    resolution = RotationWeaponAttackBuildEvaluationResolution(
        build=object(),  # type: ignore[arg-type]
        evaluations=(("front", "front-eval"), ("back", "back-eval")),  # type: ignore[arg-type]
        unresolved=(),
    )
    return dd_support.RotationGenerateDDCanonicalWeaponAttackProviderFactory(
        database_path="unused.db",
        evaluation_service=_EvaluationService(resolution),  # type: ignore[arg-type]
    )


def test_factory_promotes_verified_scheduler_reservation_to_heavy_completion(monkeypatch) -> None:
    factory = _factory(monkeypatch)
    _, heavy = factory.providers_for(
        player_build=object(),  # type: ignore[arg-type]
        static_context=_StaticContext(),
        target_resistance=18200.0,
    )
    candidate = _candidate(reserved=True)
    action = candidate.plan.actions[0]

    result = heavy.evaluate_action(candidate=candidate, action=action)

    assert result.unresolved == ()
    assert result.damage_value == 500.0
    assert len(_FakeHeavyAttackService.calls) == 1
    call = _FakeHeavyAttackService.calls[0]
    assert call["evaluation"] == "front-eval"
    assert call["evaluation_context"].target_resistance == 18200.0
    assert len(call["completion_evidence"]) == 1
    evidence = call["completion_evidence"][0]
    assert evidence.action_time_seconds == 1.0
    assert evidence.action_sequence == 0
    assert evidence.completion_time_seconds == 2.8
    assert evidence.fully_charged is True


def test_factory_does_not_promote_unreserved_heavy_to_completed_damage(monkeypatch) -> None:
    factory = _factory(monkeypatch)
    _, heavy = factory.providers_for(
        player_build=object(),  # type: ignore[arg-type]
        static_context=_StaticContext(),
        target_resistance=18200.0,
    )
    candidate = _candidate(reserved=False)
    action = candidate.plan.actions[0]

    result = heavy.evaluate_action(candidate=candidate, action=action)

    assert result.damage_value is None
    assert result.unresolved == ("missing verified heavy completion",)
    assert _FakeHeavyAttackService.calls[0]["completion_evidence"] == ()
