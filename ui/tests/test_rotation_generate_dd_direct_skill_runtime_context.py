from dataclasses import dataclass
from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
import ui.rotation_generate_dd_role_evidence_support as dd_support


@dataclass(frozen=True)
class _Context:
    combat_state: CombatState = CombatState()
    target_resistance: float | None = None
    fight_duration: float = 0.0


@dataclass(frozen=True)
class _RuntimeResult:
    resolved: bool
    context: _Context | None
    unresolved: tuple[str, ...] = ()
    active_bar: str = "front"


class _StaticContext:
    def context_at(self, *args, **kwargs):
        raise AssertionError("runtime-bound direct skill must not fall back to static context")


class _RecordingSkillEvaluator:
    contexts = []

    def __init__(self, *, context, **kwargs):
        del kwargs
        self.context = context
        self.contexts.append(context)

    def evaluate_action(self, *, candidate, action):
        del candidate
        return dd_support.RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=123.0,
        )


def _candidate() -> GeneratedRotationCandidate:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=4.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Venom Skull",
                bar="front",
            ),
        ),
    )
    return SimpleNamespace(plan=plan)


def test_direct_skill_uses_exact_runtime_build_context(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "RotationCandidateSkillDamageEvidenceService",
        _RecordingSkillEvaluator,
    )
    _RecordingSkillEvaluator.contexts.clear()
    calls = []
    runtime_context = _Context(
        combat_state=CombatState(active_buffs=("Magical Banner",)),
        target_resistance=999.0,
        fight_duration=1.0,
    )

    def runtime_resolver(time_seconds, sequence=None):
        calls.append((time_seconds, sequence))
        return _RuntimeResult(resolved=True, context=runtime_context)

    provider = dd_support._RotationGenerateBarAwareSkillDamageProvider(
        database_path="unused.db",
        static_context=_StaticContext(),
        target_resistance=18200.0,
        runtime_build_context_resolver=runtime_resolver,
    )
    action = _candidate().plan.actions[0]

    result = provider.evaluate_action(candidate=_candidate(), action=action)

    assert result.damage_value == 123.0
    assert calls == [(4.0, 1)]
    assert len(_RecordingSkillEvaluator.contexts) == 1
    received = _RecordingSkillEvaluator.contexts[0]
    assert received.combat_state.has_buff("Magical Banner")
    assert received.target_resistance == 18200.0
    assert received.fight_duration == 10.0


def test_direct_skill_fails_closed_when_runtime_build_context_is_unresolved(monkeypatch) -> None:
    class _ExplodingEvaluator:
        def __init__(self, **kwargs):
            raise AssertionError("unresolved runtime context must not reach skill evaluator")

    monkeypatch.setattr(
        dd_support,
        "RotationCandidateSkillDamageEvidenceService",
        _ExplodingEvaluator,
    )

    def runtime_resolver(time_seconds, sequence=None):
        del time_seconds, sequence
        return _RuntimeResult(
            resolved=False,
            context=None,
            unresolved=("runtime Banner state unavailable",),
        )

    provider = dd_support._RotationGenerateBarAwareSkillDamageProvider(
        database_path="unused.db",
        static_context=_StaticContext(),
        target_resistance=18200.0,
        runtime_build_context_resolver=runtime_resolver,
    )
    action = _candidate().plan.actions[0]

    result = provider.evaluate_action(candidate=_candidate(), action=action)

    assert result.damage_value is None
    assert result.unresolved == ("runtime Banner state unavailable",)
