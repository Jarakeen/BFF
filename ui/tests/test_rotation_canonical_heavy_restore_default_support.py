from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_canonical_evidence_bundle_support import (
    RotationCanonicalEvidenceBundleSupport,
)
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
    RotationSelectedEncounterEvidenceSupport,
)


class _GuideService:
    def get(self, encounter_id: str):
        return SimpleNamespace(encounter_id=encounter_id, name="Test Boss")


class _DemandService:
    def project(self, **_kwargs):
        return SimpleNamespace(demands=(), unresolved=())


class _BundleSupport:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_evidence_bundle_defaults_to_canonical_heavy_restore_derivation() -> None:
    support = RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(),  # type: ignore[arg-type]
        demand_service=_DemandService(),  # type: ignore[arg-type]
    )

    bundle = support.build(
        encounter_id="test-boss",
        demand_policies=(),
        evaluator_resolver=object(),  # type: ignore[arg-type]
        scorecard_resolver=object(),  # type: ignore[arg-type]
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert bundle.ready is True
    assert bundle.restoration_resolver is None


def test_selected_encounter_inputs_do_not_require_hand_built_restore_math() -> None:
    inputs = RotationSelectedEncounterEvidenceInputs(
        demand_policies=(),
        evaluator_resolver=object(),  # type: ignore[arg-type]
        scorecard_resolver=object(),  # type: ignore[arg-type]
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )
    backing = _BundleSupport()
    support = RotationSelectedEncounterEvidenceSupport(
        bundle_support=backing,  # type: ignore[arg-type]
    )

    result = support.build(encounter_id="test-boss", inputs=inputs)

    assert result is backing.result
    assert backing.calls[0]["restoration_resolver"] is None
