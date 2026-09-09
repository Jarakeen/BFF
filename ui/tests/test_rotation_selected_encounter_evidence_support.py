from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
    RotationSelectedEncounterEvidenceSupport,
)


class _BundleSupport:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _inputs() -> RotationSelectedEncounterEvidenceInputs:
    return RotationSelectedEncounterEvidenceInputs(
        demand_policies=("burst-policy", "block-policy"),  # type: ignore[arg-type]
        evaluator_resolver="evaluator",  # type: ignore[arg-type]
        scorecard_resolver="scorecard",  # type: ignore[arg-type]
        resource=ResourceType.MAGICKA,
        maximum_amount=32100,
        trigger_fraction=0.37,
        restoration_resolver="restoration",  # type: ignore[arg-type]
        options=("refresh-option",),  # type: ignore[arg-type]
        requirements=("minor-berserk",),  # type: ignore[arg-type]
        passives=("class-passive", "armor-passive"),  # type: ignore[arg-type]
        wait_decision_factory="wait-factory",  # type: ignore[arg-type]
        reserve_assessment_resolver="reserve",  # type: ignore[arg-type]
        max_iterations=7,
        baseline_id="selected-encounter",
        knowledge_gaps=("known-gap",),  # type: ignore[arg-type]
        coverage_report="coverage",  # type: ignore[arg-type]
        coverage_dependency_keys=("skill:combat_prayer", "set:serpents_disdain"),
    )


def test_selected_encounter_support_forwards_exact_canonical_identity_and_inputs() -> None:
    bundle = object()
    backing = _BundleSupport(bundle)
    support = RotationSelectedEncounterEvidenceSupport(bundle_support=backing)  # type: ignore[arg-type]

    result = support.build(encounter_id="  xalvakka_hm  ", inputs=_inputs())

    assert result is bundle
    assert len(backing.calls) == 1
    call = backing.calls[0]
    assert call["encounter_id"] == "xalvakka_hm"
    assert call["demand_policies"] == ("burst-policy", "block-policy")
    assert call["evaluator_resolver"] == "evaluator"
    assert call["scorecard_resolver"] == "scorecard"
    assert call["resource"] is ResourceType.MAGICKA
    assert call["maximum_amount"] == 32100
    assert call["trigger_fraction"] == 0.37
    assert call["restoration_resolver"] == "restoration"
    assert call["options"] == ("refresh-option",)
    assert call["requirements"] == ("minor-berserk",)
    assert call["passives"] == ("class-passive", "armor-passive")
    assert call["wait_decision_factory"] == "wait-factory"
    assert call["reserve_assessment_resolver"] == "reserve"
    assert call["max_iterations"] == 7
    assert call["baseline_id"] == "selected-encounter"
    assert call["knowledge_gaps"] == ("known-gap",)
    assert call["coverage_report"] == "coverage"
    assert call["coverage_dependency_keys"] == (
        "skill:combat_prayer",
        "set:serpents_disdain",
    )


@pytest.mark.parametrize("encounter_id", [None, "", "   "])
def test_selected_encounter_support_refuses_missing_identity(encounter_id) -> None:
    backing = _BundleSupport(object())
    support = RotationSelectedEncounterEvidenceSupport(bundle_support=backing)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="select an encounter"):
        support.build(encounter_id=encounter_id, inputs=_inputs())

    assert backing.calls == []


def test_selected_encounter_support_preserves_unready_bundle_without_reinterpretation() -> None:
    bundle = SimpleNamespace(
        ready=False,
        unresolved=("burn_phase: canonical timeline fact is not reviewed",),
    )
    backing = _BundleSupport(bundle)
    support = RotationSelectedEncounterEvidenceSupport(bundle_support=backing)  # type: ignore[arg-type]

    result = support.build(encounter_id="reef_guardian_hm", inputs=_inputs())

    assert result is bundle
    assert result.ready is False
    assert result.unresolved == (
        "burn_phase: canonical timeline fact is not reviewed",
    )
