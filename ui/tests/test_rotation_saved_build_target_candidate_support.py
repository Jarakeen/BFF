from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetKind,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_saved_build_action_target_service import (
    RotationSavedBuildActionTargetEvidence,
)
from ui.rotation_saved_build_target_candidate_support import (
    RotationSavedBuildTargetCandidateSupport,
)


@dataclass(frozen=True)
class _Scorecard:
    target_assessment: object | None = None
    candidate_specific_unresolved: tuple[str, ...] = ()

    @property
    def target_violations(self):
        if self.target_assessment is None:
            return ()
        return self.target_assessment.violations


class _CanonicalCandidates:
    static_context_service = object()

    def run_effects(self, **kwargs):
        resolver = kwargs["scorecard_resolver"]
        return resolver(SimpleNamespace(plan=kwargs["seed_plan"]))


class _TargetService:
    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = 0

    def resolve(self, _player_build):
        self.calls += 1
        return self.evidence


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _window(target_kind: RotationTargetKind) -> RotationTargetStateWindow:
    return RotationTargetStateWindow(
        name="Known target",
        start_seconds=0.0,
        end_seconds=30.0,
        target_kind=target_kind,
    )


def test_resolved_saved_target_is_enforced_on_final_plan() -> None:
    evidence = RotationSavedBuildActionTargetEvidence(
        target_requirements=(
            RotationActionTargetRequirement(
                action_name="Force Pulse",
                action_kind=RotationActionKind.SKILL,
                allowed_targets=(RotationTargetKind.ENEMY,),
            ),
        ),
    )
    support = RotationSavedBuildTargetCandidateSupport(
        canonical_candidates=_CanonicalCandidates(),
        target_service=_TargetService(evidence),
    )
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Force Pulse", "front"),
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=plan,
        scorecard_resolver=lambda _snapshot: _Scorecard(),
        target_state_windows=(_window(RotationTargetKind.ALLY),),
    )

    assert len(result.target_violations) == 1
    assert result.target_violations[0].observed_target is RotationTargetKind.ALLY
    assert result.candidate_specific_unresolved == ()


def test_unresolved_saved_target_is_candidate_specific_only_when_used() -> None:
    evidence = RotationSavedBuildActionTargetEvidence(
        unresolved=("canonical skill target describes topology",),
        unresolved_action_names=("Combat Prayer",),
    )
    support = RotationSavedBuildTargetCandidateSupport(
        canonical_candidates=_CanonicalCandidates(),
        target_service=_TargetService(evidence),
    )
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=plan,
        scorecard_resolver=lambda _snapshot: _Scorecard(),
        target_state_windows=(_window(RotationTargetKind.ALLY),),
    )

    assert result.target_violations == ()
    assert result.candidate_specific_unresolved == (
        "canonical action target unresolved for used action: Combat Prayer",
    )


def test_unused_unresolved_target_remains_nonblocking_for_candidate() -> None:
    evidence = RotationSavedBuildActionTargetEvidence(
        unresolved=("canonical skill target describes topology",),
        unresolved_action_names=("Combat Prayer",),
    )
    support = RotationSavedBuildTargetCandidateSupport(
        canonical_candidates=_CanonicalCandidates(),
        target_service=_TargetService(evidence),
    )
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Force Pulse", "front"),
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=plan,
        scorecard_resolver=lambda _snapshot: _Scorecard(),
        target_state_windows=(_window(RotationTargetKind.ENEMY),),
    )

    assert result.candidate_specific_unresolved == ()


def test_no_target_state_windows_preserves_existing_path_without_resolving_targets() -> None:
    service = _TargetService(RotationSavedBuildActionTargetEvidence())
    inner = _CanonicalCandidates()
    support = RotationSavedBuildTargetCandidateSupport(
        canonical_candidates=inner,
        target_service=service,
    )
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Force Pulse", "front"),
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=plan,
        scorecard_resolver=lambda _snapshot: _Scorecard(),
    )

    assert result == _Scorecard()
    assert service.calls == 0
    assert support.static_context_service is inner.static_context_service
