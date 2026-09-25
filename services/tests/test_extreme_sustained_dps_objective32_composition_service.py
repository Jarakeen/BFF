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


def _runtime_state_frontier_resolver(
    *,
    supplemental_event_denominator_proven=True,
    supplemental_history_denominator_proven=True,
):
    runtime_effect_universe = SimpleNamespace(
        weapon_enchantment_runtime_source_service=object(),
        weapon_enchantment_runtime_variant_service=object(),
    )
    return SimpleNamespace(
        scenario_frontier=SimpleNamespace(
            runtime_effect_universe=runtime_effect_universe,
            runtime_effect_scaling=object(),
            weapon_enchantment_activation_service=object(),
            weapon_enchantment_cooldown_policy_resolver=object(),
            weapon_poison_activation_service=object(),
            weapon_poison_consequence_resolver=object(),
        ),
        supplemental_event_denominator_proven=supplemental_event_denominator_proven,
        supplemental_history_denominator_proven=supplemental_history_denominator_proven,
    )


def _kwargs():
    return {
        "structural_families": object(),
        "structural_materialization": object(),
        "gear_adapter": object(),
        "late_adapter": SimpleNamespace(
            poisons=object(),
            poison_tiers=object(),
            axes=lambda: (
                SimpleNamespace(canonical_axes=("weapon_poisons",)),
                SimpleNamespace(canonical_axes=("weapon_poison_tiers",)),
            ),
        ),
        "rotation_adapter": object(),
        "runtime_policy_adapter": _RuntimePolicyAdapter(),
        "runtime_evaluation": object(),
        "mundus_food_adapter": object(),
        "encounter_policy_adapter": object(),
        "finalized_potion_evidence_resolver": _PotionEvidence(proven=True),
        "runtime_state_frontier_resolver": _runtime_state_frontier_resolver(),
        "potion_cooldown_resolver": object(),
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
    assert any("canonical fail-closed cooldown authority" in row for row in result.evidence)
    assert any(
        "Weapon-poison activation and explicit consequence authorities" in row
        for row in result.evidence
    )
    assert result.pipeline.runtime_state_frontier_resolver is not None
    assert any(
        "Finalized potion timing is appended after runtime-policy axes" in row
        for row in result.evidence
    )
    assert any(
        "weapon-poison" in row
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





def test_composition_refuses_unproven_supplemental_runtime_event_denominator() -> None:
    kwargs = _kwargs()
    kwargs["runtime_state_frontier_resolver"] = _runtime_state_frontier_resolver(
        supplemental_event_denominator_proven=False,
    )

    with pytest.raises(
        ValueError,
        match="proven-complete supplemental runtime-event denominator",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)


def test_composition_refuses_unproven_supplemental_runtime_history_denominator() -> None:
    kwargs = _kwargs()
    kwargs["runtime_state_frontier_resolver"] = _runtime_state_frontier_resolver(
        supplemental_history_denominator_proven=False,
    )

    with pytest.raises(
        ValueError,
        match="proven-complete supplemental runtime-history denominator",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)

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



def test_composition_requires_reviewed_potion_cooldown_authority() -> None:
    kwargs = _kwargs()
    kwargs["potion_cooldown_resolver"] = None

    with pytest.raises(ValueError, match="requires a canonical potion cooldown resolver"):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)



@pytest.mark.parametrize(
    ("attribute", "message"),
    (
        (
            "weapon_enchantment_activation_service",
            "weapon-enchantment activation-event resolution",
        ),
        (
            "weapon_enchantment_cooldown_policy_resolver",
            "weapon-enchantment cooldown-policy authority",
        ),
        (
            "weapon_poison_activation_service",
            "weapon-poison activation-event authority",
        ),
        (
            "weapon_poison_consequence_resolver",
            "weapon-poison consequence authority",
        ),
    ),
)
def test_composition_requires_weapon_enchantment_runtime_authorities(attribute, message):
    kwargs = _kwargs()
    resolver = kwargs["runtime_state_frontier_resolver"]
    setattr(resolver.scenario_frontier, attribute, None)

    with pytest.raises(ValueError, match=message):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)


@pytest.mark.parametrize(
    "attribute",
    (
        "weapon_enchantment_runtime_source_service",
        "weapon_enchantment_runtime_variant_service",
    ),
)
def test_composition_requires_dedicated_weapon_enchantment_runtime_universe(attribute):
    kwargs = _kwargs()
    resolver = kwargs["runtime_state_frontier_resolver"]
    setattr(resolver.scenario_frontier.runtime_effect_universe, attribute, None)

    with pytest.raises(
        ValueError,
        match="dedicated canonical weapon-enchantment runtime source and variant projection",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)

def test_composition_requires_generated_weapon_poison_selection_frontier() -> None:
    kwargs = _kwargs()
    kwargs["late_adapter"] = SimpleNamespace(
        poisons=None,
        poison_tiers=object(),
        axes=lambda: (
            SimpleNamespace(canonical_axes=("weapon_poisons",)),
            SimpleNamespace(canonical_axes=("weapon_poison_tiers",)),
        ),
    )

    with pytest.raises(
        ValueError,
        match="canonical generated weapon-poison selection frontier",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)



def test_composition_requires_generated_weapon_poison_tier_frontier() -> None:
    kwargs = _kwargs()
    kwargs["late_adapter"] = SimpleNamespace(
        poisons=object(),
        poison_tiers=None,
        axes=lambda: (
            SimpleNamespace(canonical_axes=("weapon_poisons",)),
            SimpleNamespace(canonical_axes=("weapon_poison_tiers",)),
        ),
    )

    with pytest.raises(
        ValueError,
        match="canonical generated weapon-poison tier frontier",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)


@pytest.mark.parametrize(
    ("missing_axis", "remaining_axis"),
    (
        ("weapon_poisons", "weapon_poison_tiers"),
        ("weapon_poison_tiers", "weapon_poisons"),
    ),
)
def test_composition_requires_late_adapter_to_physically_publish_poison_axes(
    missing_axis,
    remaining_axis,
):
    kwargs = _kwargs()
    kwargs["late_adapter"] = SimpleNamespace(
        poisons=object(),
        poison_tiers=object(),
        axes=lambda: (
            SimpleNamespace(canonical_axes=(remaining_axis,)),
        ),
    )

    with pytest.raises(
        ValueError,
        match=f"physically publish canonical axis: {missing_axis}",
    ):
        ExtremeSustainedDPSObjective32CompositionService.compose(**kwargs)
