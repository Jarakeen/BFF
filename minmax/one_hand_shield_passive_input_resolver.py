from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .block_stats import BlockCostModifier
from .combat_state import IncomingAttackState
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs


_ONE_HANDED_TYPES = {"sword", "axe", "mace", "dagger"}
_LEGACY_ONE_HAND_SHIELD = "one hand and shield"
_DEFENSIVE_STANCE = "defensive stance"


class OneHandShieldPassiveInputResolver:
    """Apply verified One Hand and Shield standing and contextual effects.

    Max-rank passive ownership is explicit for Fortress, Sword and Board, and
    Deflect Bolts. Defensive Stance is proven by the skill being slotted on the
    active bar and by a qualifying shield setup on that bar.
    """

    @staticmethod
    def _active_bar_has_one_hand_and_shield(build: PlayerBuild, active_bar: str) -> bool:
        main, offhand = build.active_weapon_slots(active_bar)
        main_type = str(main.WeaponType or "").strip().casefold()
        offhand_type = str(offhand.WeaponType or "").strip().casefold()

        if main_type == _LEGACY_ONE_HAND_SHIELD and offhand.is_empty:
            return True
        return main_type in _ONE_HANDED_TYPES and offhand_type == "shield"

    @staticmethod
    def _active_bar_has_defensive_stance(build: PlayerBuild, active_bar: str) -> bool:
        skills = build.BackBarSkills if str(active_bar or "front").casefold() == "back" else build.FrontBarSkills
        return any(str(skill or "").strip().casefold() == _DEFENSIVE_STANCE for skill in skills)

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        passives_owned: bool = False,
        incoming_attack: IncomingAttackState = IncomingAttackState(),
    ) -> GearCalculationInputs:
        if not self._active_bar_has_one_hand_and_shield(build, active_bar):
            return result

        core = result.core
        applied = result.applied_effect_count

        if passives_owned:
            block_cost = replace(
                core.block_cost,
                sequential_modifiers=core.block_cost.sequential_modifiers
                + (BlockCostModifier("One Hand and Shield: Fortress", -0.36),),
            )
            mitigation_modifiers = core.block_mitigation.amount_blocked_modifiers + (
                ("One Hand and Shield: Sword and Board", 0.20),
            )
            if incoming_attack.qualifies_for_deflect_bolts:
                mitigation_modifiers += (("One Hand and Shield: Deflect Bolts", 0.14),)
                applied += 1

            block_mitigation = replace(
                core.block_mitigation,
                amount_blocked_modifiers=mitigation_modifiers,
            )
            damage = StatContribution("One Hand and Shield: Sword and Board", 0.05)
            core = replace(
                core,
                block_cost=block_cost,
                block_mitigation=block_mitigation,
                weapon_damage=replace(
                    core.weapon_damage,
                    percent=core.weapon_damage.percent + (damage,),
                ),
                spell_damage=replace(
                    core.spell_damage,
                    percent=core.spell_damage.percent + (damage,),
                ),
            )
            applied += 4

        if self._active_bar_has_defensive_stance(build, active_bar):
            core = replace(
                core,
                block_cost=replace(
                    core.block_cost,
                    sequential_modifiers=core.block_cost.sequential_modifiers
                    + (BlockCostModifier("One Hand and Shield: Defensive Stance", -0.10),),
                ),
                block_mitigation=replace(
                    core.block_mitigation,
                    amount_blocked_modifiers=core.block_mitigation.amount_blocked_modifiers
                    + (("One Hand and Shield: Defensive Stance", 0.10),),
                ),
            )
            applied += 2

        if core == result.core:
            return result
        return replace(result, core=core, applied_effect_count=applied)
