from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_objective32_composition_service import (
    ExtremeSustainedDPSObjective32CompositionService,
)


class _RuntimePolicyAdapter:
    require_complete_heavy_attack_discovery = True


class _PotionEvidence:
    def __init__(self, *, proven=True):
        self.additional_resource_event_denominator_proven = proven


def _runtime_state_frontier_resolver():
    return SimpleNamespace(
        scenario_frontier=SimpleNamespace(
            runtime_effect_universe=object(),
            runtime_effect_scaling=object(),
        )
    )


def _kwargs():
    return {
        "structural_families": object(),
        "structural_materialization": object(),
        "gear_adapter": object(),
        "late_adapter": object(),
        "rotation_adapter": object(),
        "runtime_policy_adapter": _RuntimePolicyAdapter(),
        "runtime_evaluation": object(),
        "mundus_food_adapter": object(),
        "encounter_policy_adapter": object(),
        "finalized_potion_evidence_resolver": _PotionEvidence(proven=True),
        "runtime_state_frontier_resolver": _runtime_state_frontier_resolver(),
    }


def test_composition_wires_finalized_potion_axis_into_global_objective_graph() -> None:
    result = ExtremeSustainedDPSObjective32CompositionService.compose(
        **_kwargs()
    )

    assert result.pipeline.finalized_potion_adapter is not None
    assert (
        result.pipeline.finalized_potion_evidence_resolver
        is not None
    )
    assert result.global_search.pipeline is result.pipeline
    assert result.objective32.global_search is result.global_search
    assert result.objective32.require_closure_ready_scenario is True
    assert result.objective32.potion_cooldown_resolver is not None
    assert result.pipeline.runtime_state_frontier_resolver is not None
    assert any(
        "Finalized potion timing is appended after runtime-policy axes" in row
        for row in result.evidence
    )


def test_composition_preserves_required_canonical_pipeline_adapters() -> None:
    kwargs = _kwargs()
    kwargs["mundus_food_adapter"] = "mundus-food"
    kwargs["encounter_policy_adapter"] = "encounter"

    result = ExtremeSustainedDPSObjective32CompositionService.compose(
        **kwargs
    )

    assert result.pipeline.mundus_food_adapter == "mundus-food"
    assert result.pipeline.encounter_policy_adapter == "encounter"


def test_composition_refuses_unproven_additional_resource_event_denominator() -> None:
    kwargs = _kwargs()
    kwargs["finalized_potion_evidence_resolver"] = _PotionEvidence(
        proven=False
    )

    with pytest.raises(
        ValueError,
        match="proven-complete additional resource-event denominator",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("structural_families", "structural families"),
        ("structural_materialization", "structural materialization"),
        ("gear_adapter", "generated gear and late adapters"),
        ("late_adapter", "generated gear and late adapters"),
        ("rotation_adapter", "generated rotation and runtime-policy adapters"),
        ("runtime_policy_adapter", "generated rotation and runtime-policy adapters"),
        ("runtime_evaluation", "canonical generated runtime evaluation"),
        ("mundus_food_adapter", "canonical Mundus/food adapter"),
        ("encounter_policy_adapter", "canonical encounter-policy adapter"),
        ("finalized_potion_evidence_resolver", "finalized potion timing evidence"),
        ("runtime_state_frontier_resolver", "candidate-resolved runtime-state authority"),
    ),
)
def test_composition_refuses_missing_production_authority(field, message) -> None:
    kwargs = _kwargs()
    kwargs[field] = None

    with pytest.raises(ValueError, match=message):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)



def test_composition_refuses_legacy_heavy_attack_window_mode() -> None:
    kwargs = _kwargs()
    kwargs["runtime_policy_adapter"] = object()

    with pytest.raises(
        ValueError,
        match="complete Heavy Attack discovery mode",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)



def test_composition_can_inject_reviewed_potion_cooldown_authority() -> None:
    resolver = object()
    result = ExtremeSustainedDPSObjective32CompositionService.compose(
        **_kwargs(),
        potion_cooldown_resolver=resolver,
    )

    assert result.objective32.potion_cooldown_resolver is resolver
