from __future__ import annotations

"""Resolve exact selected Decrease Health weapon-enchantment damage.

Update 23 gives one narrow weapon-enchantment damage family enough primary-source
evidence for deterministic target-side application: CP160 Legendary Decrease Health.
Other weapon-enchantment damage families remain fail-closed through the shared critical-policy path.
"""

from dataclasses import dataclass
from math import isclose

from models.combat_simulation import (
    CombatSimulationOutgoingDamage,
    CombatSimulationTargetState,
)
from services.extreme_sustained_dps_weapon_enchantment_damage_policy_service import (
    ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService,
)
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentOblivionDamageResolution:
    damage: tuple[CombatSimulationOutgoingDamage, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService:
    """Project reviewed CP160 Legendary Decrease Health damage exactly."""

    LEGENDARY_CP160_HEALTH_PERCENT = 0.0375
    LEGENDARY_CP160_DAMAGE_CAP = 4875.0

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def _legendary_quality(cls, value: object) -> bool:
        return cls._key(value) in {"gold", "legendary"}

    @classmethod
    def resolve(
        cls,
        *,
        occurrences: tuple[
            ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
            ...,
        ],
        target_state: CombatSimulationTargetState,
        target_identity: str,
    ) -> ExtremeSustainedDPSWeaponEnchantmentOblivionDamageResolution:
        target = str(target_identity or "").strip()
        combatant = target_state.combatant(target) if target else None
        damage_policy = ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService.resolve(
            tuple(occurrences)
        )

        rows: list[CombatSimulationOutgoingDamage] = []
        evidence: list[str] = list(damage_policy.evidence)
        unresolved: list[str] = list(damage_policy.unresolved)
        inspected = 0

        for occurrence in tuple(occurrences):
            coordinate = f"{occurrence.time_seconds:g}s #{occurrence.sequence}"
            source_label = str(occurrence.source.source_label or "").strip()

            for effect in tuple(occurrence.consequences):
                if cls._key(effect.effect_type) != "damage":
                    continue
                inspected += 1

                damage_type = cls._key(effect.damage_type)
                if damage_type != "oblivion":
                    unresolved.append(
                        f"{coordinate}: {source_label} {damage_type or 'unknown'} "
                        "weapon-enchantment damage is outside the reviewed exact "
                        "Oblivion consumer"
                    )
                    continue

                if cls._key(effect.scaling_type) != "target_max_health":
                    unresolved.append(
                        f"{coordinate}: {source_label} Oblivion damage lacks reviewed "
                        "target-Max-Health scaling provenance"
                    )
                    continue

                if not cls._legendary_quality(
                    occurrence.source.enchantment_quality
                ):
                    unresolved.append(
                        f"{coordinate}: {source_label} exact Decrease Health damage "
                        "requires explicit Legendary/Gold glyph quality"
                    )
                    continue

                if cls._key(occurrence.source.item_level) != "cp160":
                    unresolved.append(
                        f"{coordinate}: {source_label} exact Decrease Health damage "
                        "requires explicit CP160 glyph level"
                    )
                    continue

                if cls._key(occurrence.source.enchantment_tier) != "truly superb":
                    unresolved.append(
                        f"{coordinate}: {source_label} exact Decrease Health damage "
                        "requires explicit Truly Superb glyph tier"
                    )
                    continue

                try:
                    imported_cap = float(effect.value)
                except (TypeError, ValueError):
                    unresolved.append(
                        f"{coordinate}: {source_label} Oblivion damage cap is non-numeric"
                    )
                    continue
                if not isclose(
                    imported_cap,
                    cls.LEGENDARY_CP160_DAMAGE_CAP,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                ):
                    unresolved.append(
                        f"{coordinate}: {source_label} imported Oblivion damage cap "
                        f"{imported_cap:g} does not match reviewed CP160 Legendary "
                        f"{cls.LEGENDARY_CP160_DAMAGE_CAP:g}"
                    )
                    continue

                if combatant is None:
                    unresolved.append(
                        f"{coordinate}: {source_label} exact Oblivion damage requires "
                        f"target state for {target or '(blank target)'}"
                    )
                    continue
                if combatant.maximum_health is None:
                    unresolved.append(
                        f"{coordinate}: {source_label} exact Oblivion damage requires "
                        "target maximum Health"
                    )
                    continue

                maximum_health = float(combatant.maximum_health)
                amount = min(
                    maximum_health * cls.LEGENDARY_CP160_HEALTH_PERCENT,
                    cls.LEGENDARY_CP160_DAMAGE_CAP,
                )
                rows.append(
                    CombatSimulationOutgoingDamage(
                        time_seconds=float(occurrence.time_seconds),
                        sequence=int(occurrence.sequence),
                        source=source_label,
                        recipient=target,
                        amount=amount,
                        damage_type="oblivion",
                    )
                )
                evidence.append(
                    f"{coordinate}: {source_label} resolved Decrease Health as "
                    f"min(3.75% of {maximum_health:g}, 4875) = {amount:g}"
                )

        ordered = tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.time_seconds,
                    row.sequence,
                    row.source.casefold(),
                ),
            )
        )
        return ExtremeSustainedDPSWeaponEnchantmentOblivionDamageResolution(
            damage=ordered,
            evidence=(
                f"Selected weapon-enchantment damage consequences inspected: {inspected}",
                f"Exact CP160 Legendary Decrease Health occurrences resolved: {len(ordered)}",
                "Reviewed player-sourced Oblivion damage bypasses ordinary positive/negative damage bonuses.",
                *tuple(evidence),
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentOblivionDamageResolution",
    "ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService",
]
