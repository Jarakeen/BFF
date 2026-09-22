from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_target_type import SupportTargetType
from services.extreme_sustained_dps_closure_inventory_service import (
    ExtremeSustainedDPSClosureInventoryService,
)
from services.extreme_sustained_dps_runtime_effect_relevance_service import (
    ExtremeSustainedDPSRuntimeEffectRelevanceService,
)


def test_closure_inventory_separates_source_and_math_runtime_blockers() -> None:
    source_gap = EffectVariant(
        name="scaled_resistance_debuff",
        layer=EffectLayer.PROC,
        source="Scaled Debuff",
        trigger="damage_dealt",
        duration=5.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=6000.0,
        scaling="up to 6000 from unresolved source state",
    )
    math_gap = EffectVariant(
        name="mystery_runtime_power",
        layer=EffectLayer.PROC,
        source="Mystery Proc",
        trigger="damage_dealt",
        duration=5.0,
    )
    relevance = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify(
        (source_gap, math_gap)
    )

    inventory = ExtremeSustainedDPSClosureInventoryService.build(
        relevance=relevance,
        mechanics_dependency_keys=(),
    )

    assert len(inventory.source_data_blockers) == 1
    assert "unresolved scaling" in inventory.source_data_blockers[0]
    assert len(inventory.math_review_blockers) == 1
    assert "no reviewed sustained-DPS relevance disposition" in inventory.math_review_blockers[0]
    assert inventory.mechanics_blockers == ()
    assert inventory.closure_ready is False
    assert inventory.blocking_count == 2


def test_closure_inventory_surfaces_weapon_enchantment_cadence_as_blocking() -> None:
    inventory = ExtremeSustainedDPSClosureInventoryService.build(
        mechanics_dependency_keys=("weapon_enchantments:runtime_cadence",),
    )

    assert inventory.source_data_blockers == ()
    assert inventory.math_review_blockers == ()
    assert len(inventory.mechanics_blockers) == 1
    assert inventory.mechanics_blockers[0].key == "weapon_enchantments:runtime_cadence"
    assert inventory.mechanics_blockers[0].blocking is True
    assert inventory.closure_ready is False


def test_closure_inventory_keeps_partial_mechanics_as_advisory() -> None:
    inventory = ExtremeSustainedDPSClosureInventoryService.build(
        mechanics_dependency_keys=("effect_duration:build_modifiers",),
    )

    assert inventory.mechanics_blockers == ()
    assert len(inventory.mechanics_advisories) == 1
    assert inventory.mechanics_advisories[0].key == "effect_duration:build_modifiers"
    assert inventory.closure_ready is True
    assert inventory.blocking_count == 0


def test_default_objective32_inventory_names_open_closure() -> None:
    inventory = ExtremeSustainedDPSClosureInventoryService.build()

    assert any(
        gap.key == "weapon_enchantments:runtime_cadence"
        for gap in inventory.mechanics_blockers
    )
    assert inventory.closure_ready is False
    assert any("closure inventory remains open" in row for row in inventory.evidence)
