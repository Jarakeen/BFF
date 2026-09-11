from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.combat_state import CombatState
from minmax.resource_costs import ResourceType
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def __init__(self, canonical_build) -> None:
        self.canonical_build = canonical_build

    def adapt(self, saved_build, *, character_id=None):
        return SavedBuildAdaptation(build=self.canonical_build, unresolved=())


class _EvidenceService:
    def __init__(self, resolution) -> None:
        self.resolution = resolution

    def resolve(self, saved_build):
        return self.resolution


class _StaticContextService:
    def __init__(self) -> None:
        self.calls = []

    def resolve(self, saved_build, *, combat_state: CombatState):
        self.calls.append((saved_build, combat_state))
        return SimpleNamespace(
            resolved=False,
            unresolved=("state-specific static context sentinel",),
        )


class _Pipeline:
    def __init__(self) -> None:
        self.calls = []

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("pipeline must not run when static context is unresolved")


def test_explicit_combat_state_reaches_canonical_static_rotation_context() -> None:
    saved_build = object()
    canonical_build = object()
    combat_state = CombatState(
        in_combat=True,
        active_buffs=("Major Sorcery",),
    )
    static_context_service = _StaticContextService()
    pipeline = _Pipeline()

    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(canonical_build),
        pipeline=pipeline,
        static_context_service=static_context_service,
        action_timing_service=_EvidenceService(
            SimpleNamespace(
                cooldown_requirements=(),
                occupancy_requirements=(),
                unresolved_action_names=(),
            )
        ),
        action_range_service=_EvidenceService(
            SimpleNamespace(
                range_requirements=(),
                unresolved_action_names=(),
            )
        ),
        action_slot_service=_EvidenceService(
            SimpleNamespace(
                slot_requirements=(),
                unresolved=(),
            )
        ),
    )

    result = support.run_effects(
        player_build=saved_build,
        seed_plan=object(),
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        combat_state=combat_state,
    )

    assert static_context_service.calls == [(saved_build, combat_state)]
    assert pipeline.calls == []
    assert result.pipeline_result is None
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert any(
        "state-specific static context sentinel" in reason
        for reason in result.validation.reasons
    )
