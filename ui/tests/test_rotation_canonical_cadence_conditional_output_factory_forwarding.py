from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from ui.rotation_canonical_cadence_orchestration_support import (
    RotationCanonicalCadenceOrchestrationSupport,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(candidate_result="candidate-result")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Render:
    def build(self, _result):
        return None


def test_cadence_orchestration_forwards_bundle_output_condition_factory() -> None:
    canonical = _CanonicalCandidates()
    support = RotationCanonicalCadenceOrchestrationSupport(
        canonical_candidates=canonical,  # type: ignore[arg-type]
        canonical_render=_Render(),  # type: ignore[arg-type]
    )

    def resolver_factory(_plan):
        return lambda _event: frozenset()

    bundle = RotationCanonicalEvidenceBundle(
        encounter_id="test-encounter",
        encounter_name="Test Encounter",
        demands=(),
        options=(),
        requirements=(),
        passives=(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        runtime_output_condition_context_resolver_factory=resolver_factory,
    )

    result = support.run(
        player_build=PlayerBuild(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD"),
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=bundle,
    )

    assert result.canonical_result is canonical.result
    assert result.canonical_evidence is None
    assert len(canonical.calls) == 1
    assert (
        canonical.calls[0]["runtime_output_condition_context_resolver_factory"]
        is resolver_factory
    )
