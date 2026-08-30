from __future__ import annotations

from dataclasses import replace

from models.build_model import GearSlot, PlayerBuild

from .block_stats import BlockCostModifier
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs


_ONE_HANDED_TYPES = {"sword", "axe", "mace", "dagger"}
_LEGACY_ONE_HAND_SHIELD = "one hand and shield"


class OneHandShieldPassiveInputResolver:
    """Apply verified max-rank One Hand and Shield standing passives.

    Ownership is explicit and applicability is active-bar equipment dependent.
    Conditional/slotted passives such as Defensive Stance are intentionally not
    handled here.
    """

    @staticmethod
    def _active_bar_has_one_hand_and_shield(build: PlayerBuild, active_bar: str) -> bool:
        main, offhand = build.active_weapon_slots(active_bar)
        main_type = str(main.WeaponType or "").strip().casefold()
        offhand_type = str(offhand.WeaponType or "").strip().casefold()

        if main_type == _LEGACY_ONE_HAND_SHIELD and offhand.is_empty:
            return True
        return main_type in _ONE_HANDED_TYPES and offhand_type == "shield"

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        passives_owned: bool = False,
    ) -> GearCalculationInputs:
        if not passives_owned or not self._active_bar_has_one_hand_and_shield(build, active_bar):
            return result

        block_cost = replace(
            result.core.block_cost,
            sequential_modifiers=result.core.block_cost.sequential_modifiers
            + (BlockCostModifier("One Hand and Shield: Fortress", -0.36),),
        )
        block_mitigation = replace(
            result.core.block_mitigation,
            amount_blocked_modifiers=result.core.block_mitigation.amount_blocked_modifiers
            + (("One Hand and Shield: Sword and Board", 0.20),),
        )
        damage = StatContribution("One Hand and Shield: Sword and Board", 0.05)
        core = replace(
            result.core,
            block_cost=block_cost,
            block_mitigation=block_mitigation,
            weapon_damage=replace(
                result.core.weapon_damage,
                percent=result.core.weapon_damage.percent + (damage,),
            ),
            spell_damage=replace(
                result.core.spell_damage,
                percent=result.core.spell_damage.percent + (damage,),
            ),
        )
        return replace(result, core=core, applied_effect_count=result.applied_effect_count + 4)
