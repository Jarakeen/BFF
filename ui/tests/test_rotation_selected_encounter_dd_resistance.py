from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
    RotationSelectedEncounterEvidenceSupport,
)


class _BundleSupport:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(marker="bundle")

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_selected_encounter_forwards_explicit_dd_target_resistance() -> None:
    bundle = _BundleSupport()
    support = RotationSelectedEncounterEvidenceSupport(
        bundle_support=bundle,  # type: ignore[arg-type]
    )
    inputs = RotationSelectedEncounterEvidenceInputs(
        demand_policies=(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        target_resistance=18200.0,
    )

    result = support.build(encounter_id="test_encounter", inputs=inputs)

    assert result is bundle.result
    assert bundle.calls[0]["target_resistance"] == 18200.0


def test_selected_encounter_preserves_unknown_dd_target_resistance() -> None:
    bundle = _BundleSupport()
    support = RotationSelectedEncounterEvidenceSupport(
        bundle_support=bundle,  # type: ignore[arg-type]
    )
    inputs = RotationSelectedEncounterEvidenceInputs(
        demand_policies=(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
    )

    support.build(encounter_id="test_encounter", inputs=inputs)

    assert bundle.calls[0]["target_resistance"] is None
