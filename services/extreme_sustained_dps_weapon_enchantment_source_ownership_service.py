from __future__ import annotations

"""Resolve weapon-enchantment ownership for one exact activation opportunity.

Update 19 proves that delayed weapon-ability damage keeps the enchantment belonging
to the weapon bar that fired the ability. This service narrows candidate enchantment
EffectVariants by that preserved source-bar provenance. It does not choose between
multiple same-bar candidates, infer a Dual Wield hand, or resolve cooldown state.
"""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentSourceOwnership:
    activation_event: object
    candidates: tuple[EffectVariant, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService:
    """Narrow enchantment candidates to the source weapon bar of an activation."""

    @staticmethod
    def _bar(effect: EffectVariant) -> str | None:
        value = getattr(effect.active_bar, "value", effect.active_bar)
        text = str(value or "").strip().casefold()
        return text or None

    def resolve(
        self,
        *,
        activation_event: object,
        enchantment_effects: tuple[EffectVariant, ...],
    ) -> ExtremeSustainedDPSWeaponEnchantmentSourceOwnership:
        source_bar = str(
            getattr(activation_event, "source_bar", None) or ""
        ).strip().casefold()
        if source_bar not in {"front", "back"}:
            return ExtremeSustainedDPSWeaponEnchantmentSourceOwnership(
                activation_event=activation_event,
                candidates=(),
                unresolved=(
                    "weapon-enchantment source ownership requires front/back source-bar provenance",
                ),
            )

        unresolved: list[str] = []
        owned: list[EffectVariant] = []
        for effect in tuple(enchantment_effects):
            effect_bar = self._bar(effect)
            if effect_bar is None:
                unresolved.append(
                    f"weapon-enchantment effect lacks source-bar ownership: {effect.source}"
                )
                continue
            if effect_bar not in {"front", "back"}:
                unresolved.append(
                    f"weapon-enchantment effect has unsupported source bar {effect_bar!r}: {effect.source}"
                )
                continue
            if effect_bar == source_bar:
                owned.append(effect)

        if unresolved:
            return ExtremeSustainedDPSWeaponEnchantmentSourceOwnership(
                activation_event=activation_event,
                candidates=(),
                evidence=(
                    f"Activation source bar: {source_bar}",
                    f"Weapon-enchantment effects inspected: {len(tuple(enchantment_effects))}",
                ),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        return ExtremeSustainedDPSWeaponEnchantmentSourceOwnership(
            activation_event=activation_event,
            candidates=tuple(owned),
            evidence=(
                f"Activation source bar: {source_bar}",
                f"Weapon-enchantment effects inspected: {len(tuple(enchantment_effects))}",
                f"Source-owned enchantment candidates: {len(owned)}",
                "Source-bar ownership narrows candidates but does not choose a Dual Wield hand or prove cooldown availability",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentSourceOwnership",
    "ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService",
]
