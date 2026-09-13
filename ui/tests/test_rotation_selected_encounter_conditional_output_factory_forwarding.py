from __future__ import annotations

from minmax.resource_costs import ResourceType
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
    RotationSelectedEncounterEvidenceSupport,
)


class _BundleSupport:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_selected_encounter_forwards_explicit_output_condition_context_factory() -> None:
    bundle_support = _BundleSupport()
    support = RotationSelectedEncounterEvidenceSupport(
        bundle_support=bundle_support,  # type: ignore[arg-type]
    )

    def resolver_factory(_plan):
        return lambda _event: frozenset()

    inputs = RotationSelectedEncounterEvidenceInputs(
        demand_policies=(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        runtime_output_condition_context_resolver_factory=resolver_factory,
    )

    result = support.build(encounter_id="test-encounter", inputs=inputs)

    assert result is bundle_support.result
    assert len(bundle_support.calls) == 1
    assert (
        bundle_support.calls[0]["runtime_output_condition_context_resolver_factory"]
        is resolver_factory
    )
