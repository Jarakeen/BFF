from __future__ import annotations

"""Project reviewed exact-duration poison named effects into Objective #32 runtime."""

from dataclasses import dataclass

from minmax.alchemy_poison_effect_semantics import poison_named_effects_for_trait
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.combat_effect_semantics import GameUpdate, normalize_game_update
from minmax.named_combat_buffs import canonical_buff_name
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionSelection,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceResolution:
    effects: tuple[EffectVariant, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.effects) and not self.unresolved


class ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService:
    """Resolve only reviewed target-side named poison effects for sustained DPS."""

    _REVIEWED_SELF_DPS_IRRELEVANT = frozenset({"minor protection"})

    def __init__(
        self,
        *,
        dilution_selection: ExtremeSustainedDPSWeaponPoisonDilutionSelection,
        game_update: GameUpdate | str = GameUpdate.U50,
    ) -> None:
        self.dilution_selection = dilution_selection
        self.game_update = normalize_game_update(game_update)

    @staticmethod
    def _norm(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _effect_key(value: str) -> str:
        return "_".join(str(value or "").strip().casefold().split())

    def resolve(
        self,
        *,
        poison_id: str,
        occurrence: ExtremeSustainedDPSWeaponPoisonProcOccurrence,
    ) -> ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceResolution:
        unresolved: list[str] = list(tuple(self.dilution_selection.unresolved))
        evidence: list[str] = list(tuple(self.dilution_selection.evidence))
        effects: list[EffectVariant] = []

        selected_poison = str(self.dilution_selection.poison_id or "").strip()
        if self._norm(poison_id) != self._norm(selected_poison):
            unresolved.append(
                f"weapon-poison consequence selection belongs to {selected_poison or '(blank)'} "
                f"but proc occurrence selected {poison_id or '(blank)'}"
            )

        if not self.dilution_selection.resolved:
            unresolved.append(
                "weapon-poison named-effect consequence projection requires exact dilution selection"
            )

        target = str(occurrence.event.target or "").strip()
        if not target:
            unresolved.append(
                "weapon-poison target-side named-effect projection requires target identity"
            )

        for selected in tuple(self.dilution_selection.effects):
            relationships = poison_named_effects_for_trait(
                selected.effect_name,
                game_update=self.game_update,
            )
            if not relationships:
                unresolved.append(
                    f"{selected_poison}: poison trait {selected.effect_name} has no reviewed "
                    f"Objective #32 named-effect relationship for {self.game_update.value}"
                )
                continue

            for relationship in relationships:
                canonical = canonical_buff_name(relationship.effect_name)
                if canonical is None:
                    unresolved.append(
                        f"{selected_poison}: poison relationship {relationship.effect_name} "
                        "has no canonical named-effect authority"
                    )
                    continue

                if relationship.target_type is SupportTargetType.SELF:
                    if self._norm(canonical) in self._REVIEWED_SELF_DPS_IRRELEVANT:
                        evidence.append(
                            f"{selected.effect_name}: self-side {canonical} is defensive-only "
                            "and irrelevant to sustained outgoing DPS"
                        )
                        continue
                    unresolved.append(
                        f"{selected_poison}: self-side poison named effect {canonical} needs "
                        "an attacker runtime projection before it can affect Objective #32"
                    )
                    continue

                if relationship.target_type is not SupportTargetType.ENEMY:
                    unresolved.append(
                        f"{selected_poison}: poison named effect {canonical} has unsupported "
                        f"target type {relationship.target_type}"
                    )
                    continue

                effects.append(
                    EffectVariant(
                        name=self._effect_key(canonical),
                        layer=EffectLayer.PROC,
                        source=selected_poison,
                        duration=float(selected.duration_seconds),
                        trigger="weapon_poison_proc",
                        target=target,
                        target_type=SupportTargetType.ENEMY,
                        category=SupportEffectCategory.DEBUFF,
                    )
                )
                evidence.append(
                    f"{selected.effect_name}: projected target-side {canonical} for "
                    f"{float(selected.duration_seconds):g}s"
                )

        unique: list[EffectVariant] = []
        for effect in effects:
            if effect not in unique:
                unique.append(effect)

        deduped_unresolved = tuple(
            dict.fromkeys(row for row in unresolved if str(row).strip())
        )
        return ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceResolution(
            effects=tuple(unique),
            evidence=tuple(dict.fromkeys(row for row in evidence if str(row).strip())),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceResolution",
    "ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService",
]
