from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


class _BuildAdapter:
    def adapt(self, _build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


class _EvidenceService:
    def __init__(self, result):
        self.result = result

    def resolve(self, _build):
        return self.result


class _Pipeline:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Validation:
    def from_candidate_pipeline_result(self, _result):
        return "validation"


def test_canonical_candidate_support_defaults_heavy_restore_to_canonical_pipeline_evidence() -> None:
    pipeline = _Pipeline()
    support = RotationCanonicalCandidateSupport(
        build_adapter=_BuildAdapter(),
        pipeline=pipeline,
        validation_support=_Validation(),
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
                unresolved=(),
                slot_requirements=(),
            )
        ),
    )
    player_build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(),
    )

    result = support.run_effects(
        player_build=player_build,
        seed_plan=plan,
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=lambda _snapshot: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert result.pipeline_result is pipeline.result
    assert result.validation == "validation"
    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["restoration_resolver"] is None
