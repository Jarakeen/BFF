from __future__ import annotations

from minmax.gear_physical_slot_realization import ExtremeWeaponSlotShape
from minmax.gear_sets import GearSetBonus
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
)
from services.extreme_sustained_dps_gear_runtime_semantic_inventory_service import (
    ExtremeSustainedDPSGearRuntimeSemanticInventoryService,
    ExtremeSustainedDPSGearSemanticKind,
)


class _Repository:
    def __init__(self, bonuses):
        self.bonuses = bonuses

    def get_bonuses(self, set_id):
        return list(self.bonuses.get(int(set_id), ()))


class _StaticResolver:
    def resolve(self, bonus, *, use_max_value=True, source=None):
        if int(bonus.id) == 1:
            return (type("_Effect", (), {"condition": None})(),)
        if int(bonus.id) == 2:
            return (type("_Effect", (), {"condition": "standing_still"})(),)
        return ()


def _realization(set_id, name, count):
    return ExtremeNamedGearSetRealization(
        topology_signature=f"{count}|unused:{12-count}",
        set_ids=(set_id,),
        set_names=(name,),
        counts=(count,),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(),
    )


def test_static_and_conditional_rows_are_classified_without_runtime_guessing() -> None:
    repo = _Repository(
        {
            100: (
                GearSetBonus(1, 100, 2, "Adds static stat"),
                GearSetBonus(2, 100, 5, "Conditional stat"),
            )
        }
    )
    state = ExtremeDualBarGearState(
        front=_realization(100, "Test Static", 5),
        back=_realization(100, "Test Static", 5),
    )
    result = ExtremeSustainedDPSGearRuntimeSemanticInventoryService(
        repo,
        static_resolver=_StaticResolver(),
    ).inventory(state)

    kinds = {row.kind for row in result.rows}
    assert ExtremeSustainedDPSGearSemanticKind.STATIC in kinds
    assert ExtremeSustainedDPSGearSemanticKind.CONDITIONAL_STATIC in kinds
    assert result.semantic_mapping_complete is True
    assert result.runtime_evaluation_required is True


def test_verified_runtime_registry_row_is_runtime_owned() -> None:
    # Spell Power Cure 5pc has a verified known-effect mapping keyed by set name.
    repo = _Repository(
        {
            200: (
                GearSetBonus(999999, 200, 5, "Runtime proc description"),
            )
        }
    )
    state = ExtremeDualBarGearState(
        front=_realization(200, "Spell Power Cure", 5),
        back=_realization(200, "Spell Power Cure", 5),
    )
    result = ExtremeSustainedDPSGearRuntimeSemanticInventoryService(
        repo,
        static_resolver=_StaticResolver(),
    ).inventory(state)

    assert all(
        row.kind is ExtremeSustainedDPSGearSemanticKind.RUNTIME
        for row in result.rows
    )
    assert result.runtime_row_count == 2
    assert result.semantic_mapping_complete is True
    assert result.runtime_evaluation_required is True


def test_unmapped_active_bonus_is_explicit_blocker() -> None:
    repo = _Repository(
        {
            300: (
                GearSetBonus(77, 300, 5, "A mysterious proc does several dramatic things"),
            )
        }
    )
    state = ExtremeDualBarGearState(
        front=_realization(300, "Unknown Set", 5),
        back=_realization(300, "Unknown Set", 5),
    )
    result = ExtremeSustainedDPSGearRuntimeSemanticInventoryService(
        repo,
        static_resolver=_StaticResolver(),
    ).inventory(state)

    assert result.unsupported_row_count == 2
    assert result.semantic_mapping_complete is False
    assert result.unresolved
    assert all(
        row.kind is ExtremeSustainedDPSGearSemanticKind.UNSUPPORTED
        for row in result.rows
    )
