from __future__ import annotations

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from services.rotation_saved_build_action_range_service import (
    RotationSavedBuildActionRangeEvidence,
)
from services.rotation_saved_build_action_slot_service import (
    RotationSavedBuildActionSlotEvidence,
)
from services.rotation_saved_build_action_timing_service import (
    RotationSavedBuildActionTimingEvidence,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


class _Adapter:
    def __init__(self) -> None:
        self.build = object()

    def adapt(self, _saved, *, character_id=None):
        return SavedBuildAdaptation(build=self.build, unresolved=())


class _EvidenceService:
    def __init__(self, result) -> None:
        self.result = result

    def resolve(self, _build):
        return self.result


class _Pipeline:
    def __init__(self) -> None:
        self.calls = []
        self.result = type(
            "PipelineResult",
            (),
            {"selected_candidate": None, "ranked_candidates": ()},
        )()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_canonical_bridge_forwards_runtime_state_resolver_factory_unchanged() -> None:
    pipeline = _Pipeline()
    factory = object()
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_timing_service=_EvidenceService(RotationSavedBuildActionTimingEvidence()),
        action_range_service=_EvidenceService(RotationSavedBuildActionRangeEvidence()),
        action_slot_service=_EvidenceService(RotationSavedBuildActionSlotEvidence()),
    )

    support.run_effects(
        player_build=object(),
        seed_plan=object(),
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        runtime_combat_state_resolver_factory=factory,
    )

    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["runtime_combat_state_resolver_factory"] is factory
