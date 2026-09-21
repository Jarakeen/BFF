from __future__ import annotations

"""Reviewed bridge from active runtime EffectVariant identities to canonical stat Effects.

This service owns no timing, trigger, cooldown, bar, or persistence logic. It receives
only EffectVariants already proven active by the shared runtime projector and converts
explicitly reviewed stat identities into the ordinary Effect pipeline used by
BuildCalculationContextFactory.
"""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeEffectProjection:
    effects: tuple[Effect, ...]
    projected_variant_count: int
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSRuntimeEffectProjectionService:
    """Convert only reviewed active runtime stat identities into canonical Effects."""

    @classmethod
    def project(
        cls,
        variants: tuple[EffectVariant, ...],
    ) -> ExtremeSustainedDPSRuntimeEffectProjection:
        effects: list[Effect] = []
        unresolved: list[str] = []
        projected = 0

        for variant in variants:
            name = str(variant.name or "").strip().casefold()
            source = str(variant.source or "").strip() or "runtime effect"
            magnitude = variant.magnitude

            if name == "weapon_spell_damage":
                if magnitude is None:
                    unresolved.append(
                        f"{source} weapon_spell_damage runtime effect has no canonical magnitude"
                    )
                    continue
                value = float(magnitude)
                effects.extend(
                    (
                        Effect(
                            operation=EffectOperation.ADD,
                            value=value,
                            source=f"{source}: active runtime Weapon Damage",
                            stat=StatId.WEAPON_DAMAGE,
                            unit=EffectUnit.FLAT,
                        ),
                        Effect(
                            operation=EffectOperation.ADD,
                            value=value,
                            source=f"{source}: active runtime Spell Damage",
                            stat=StatId.SPELL_DAMAGE,
                            unit=EffectUnit.FLAT,
                        ),
                    )
                )
                projected += 1
                continue

            unresolved.append(
                f"{source} active runtime effect {variant.name!r} has no reviewed stat projection"
            )

        return ExtremeSustainedDPSRuntimeEffectProjection(
            effects=tuple(effects),
            projected_variant_count=projected,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeEffectProjection",
    "ExtremeSustainedDPSRuntimeEffectProjectionService",
]
