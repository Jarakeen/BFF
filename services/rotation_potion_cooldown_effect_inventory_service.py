from __future__ import annotations

from dataclasses import dataclass, replace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.character_build import CharacterBuild
from services.rotation_potion_cooldown_effect_variant_service import (
    POTION_COOLDOWN_REDUCTION_EFFECT,
)


@dataclass(frozen=True)
class RotationPotionCooldownEffectInventory:
    """Build/context-wide potion-cooldown effect inventory with provenance.

    ``effects`` contains only effect variants that are safe to pass to the static
    potion-cooldown reducer. ``complete`` means the build-native sources were fully
    traversed, no discovered potion-cooldown source had unresolved availability
    topology, and the caller explicitly proved the external scenario inventory is
    complete for the modeled context.
    """

    effects: tuple[EffectVariant, ...] = ()
    unresolved: tuple[str, ...] = ()
    build_inventory_complete: bool = True
    scenario_inventory_complete: bool = False

    @property
    def complete(self) -> bool:
        return (
            self.build_inventory_complete
            and self.scenario_inventory_complete
            and not self.unresolved
        )


class RotationPotionCooldownEffectInventoryService:
    """Discover potion-cooldown effect variants without flattening runtime topology.

    This service traverses canonical CharacterBuild-native effects directly so
    ultimate/cast/slot/passive candidates are not lost merely because they are not
    active in one sampled bar state. It deliberately refuses to turn dynamic sources
    into one permanent cooldown reduction.
    """

    def resolve(
        self,
        *,
        character_build: CharacterBuild,
        passives: tuple[PassiveGrant, ...] = (),
        scenario_effects: tuple[EffectVariant, ...] = (),
        scenario_inventory_complete: bool = False,
    ) -> RotationPotionCooldownEffectInventory:
        effects: list[EffectVariant] = []
        unresolved: list[str] = []

        def consider(
            effect: EffectVariant,
            *,
            provenance: str,
            requires_active_bar_representation: bool = False,
            slot_requires_active_bar: bool = False,
        ) -> None:
            if str(effect.name or "").strip().casefold() != POTION_COOLDOWN_REDUCTION_EFFECT:
                return

            source = str(effect.source or "").strip() or "unknown source"
            topology: list[str] = []
            if requires_active_bar_representation:
                topology.append("passive requires active-bar skill-line representation")
            if slot_requires_active_bar:
                topology.append("slotted effect requires active bar")
            if effect.layer in (
                EffectLayer.CAST,
                EffectLayer.PROC,
                EffectLayer.ULTIMATE,
                EffectLayer.CONSUMABLE,
            ):
                topology.append(f"dynamic layer={effect.layer.value}")

            if topology:
                unresolved.append(
                    "canonical potion cooldown source has runtime availability topology: "
                    f"{source} [{provenance}] ({', '.join(topology)})"
                )
                return

            effects.append(effect)

        for bar in character_build.bars():
            for slot in bar.slots:
                for effect in slot.effects:
                    consider(
                        effect,
                        provenance=f"{bar.bar_id.value} slot {slot.skill_id}",
                        slot_requires_active_bar=bool(slot.requires_active_bar),
                    )
            for weapon_name, weapon in (
                ("main hand", bar.main_hand),
                ("off hand", bar.off_hand),
            ):
                if weapon is None:
                    continue
                for effect in weapon.effects:
                    consider(
                        effect,
                        provenance=f"{bar.bar_id.value} {weapon_name}",
                    )

        for piece in character_build.all_armor_pieces():
            for effect in piece.effects:
                consider(effect, provenance=f"armor:{piece.slot.value}")

        for allocation in character_build.champion_points:
            for effect in allocation.effects:
                consider(effect, provenance="champion point")

        for grant in passives:
            consider(
                grant.effect,
                provenance=f"passive:{grant.skill_line_id}",
                requires_active_bar_representation=grant.requires_active_bar_representation,
            )

        for effect in scenario_effects:
            consider(effect, provenance="scenario")

        deduped: list[EffectVariant] = []
        seen: set[EffectVariant] = set()
        for effect in effects:
            if effect in seen:
                continue
            seen.add(effect)
            deduped.append(effect)

        if not scenario_inventory_complete:
            unresolved.append(
                "external scenario potion cooldown effect inventory is not proven complete"
            )

        return RotationPotionCooldownEffectInventory(
            effects=tuple(deduped),
            unresolved=tuple(dict.fromkeys(unresolved)),
            build_inventory_complete=True,
            scenario_inventory_complete=bool(scenario_inventory_complete),
        )


__all__ = [
    "RotationPotionCooldownEffectInventory",
    "RotationPotionCooldownEffectInventoryService",
]
