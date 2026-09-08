from __future__ import annotations

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from services.rotation_saved_build_action_range_service import RotationSavedBuildActionRangeEvidence
from services.rotation_saved_build_action_slot_service import RotationSavedBuildActionSlotEvidence
from services.rotation_saved_build_action_timing_service import RotationSavedBuildActionTimingEvidence
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def adapt(self, saved, *, character_id=None):
        return SavedBuildAdaptation(build=object(), unresolved=())


class _EvidenceService:
    def __init__(self, evidence) -> None:
        self.evidence = evidence

    def resolve(self, player_build):
        return self.evidence


class _Pipeline:
    def __init__(self) -> None:
        self.called = False

    def run_effects(self, **kwargs):
        self.called = True
        raise AssertionError("pipeline must not run with ambiguous slot identity")


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(),
    )


def test_canonical_candidate_does_not_run_when_saved_slot_identity_is_ambiguous() -> None:
    pipeline = _Pipeline()
    slot_unresolved = (
        "saved-build action slot identity is ambiguous because 'Ambiguous Action' "
        "appears as both skill and ultimate",
    )
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_timing_service=_EvidenceService(RotationSavedBuildActionTimingEvidence()),
        action_range_service=_EvidenceService(RotationSavedBuildActionRangeEvidence()),
        action_slot_service=_EvidenceService(
            RotationSavedBuildActionSlotEvidence(unresolved=slot_unresolved)
        ),
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=_plan(),
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert not pipeline.called
    assert result.pipeline_result is None
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert result.action_slot_evidence.unresolved == slot_unresolved
    assert any(
        "saved-build action slot identity is unresolved" in reason
        for reason in result.validation.reasons
    )
    assert any("Ambiguous Action" in reason for reason in result.validation.reasons)
