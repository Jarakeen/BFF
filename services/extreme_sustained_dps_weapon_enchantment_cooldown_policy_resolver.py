from __future__ import annotations

"""Authoritative weapon-enchantment cooldown-policy projection for Objective #32.

This service translates canonical EffectVariants into the finite sequence frontier's
cooldown policy shape only when every cadence denominator required by runtime
simulation is authoritative. It intentionally does not infer direct-damage identity
from names, sources, magnitudes, or tooltip text.
"""

from dataclasses import dataclass
from typing import Callable

from minmax.character_build.effect_instance import EffectVariant
from minmax.support_effect_category import SupportEffectCategory
from minmax.runtime_effect_sequence import effect_variant_runtime_binding_key
from minmax.weapon_enchantment_runtime_cadence import (
    WeaponEnchantmentCadenceEvidence,
    WeaponEnchantmentEffectFamily,
    provisional_weapon_enchantment_cadence,
)
from services.extreme_sustained_dps_weapon_enchantment_cadence_family_service import (
    ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService,
)
from services.extreme_sustained_dps_weapon_enchantment_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolution:
    policies: tuple[ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver:
    """Project only authoritative cadence evidence into runtime cooldown policies."""

    def __init__(
        self,
        *,
        cadence_provider: Callable[
            [WeaponEnchantmentEffectFamily],
            WeaponEnchantmentCadenceEvidence,
        ] = provisional_weapon_enchantment_cadence,
        effect_family_resolver: Callable[
            [EffectVariant],
            WeaponEnchantmentEffectFamily | None,
        ]
        | None = None,
        runtime_source_service: object | None = None,
        cadence_family_service: object | None = None,
    ) -> None:
        if (runtime_source_service is None) != (cadence_family_service is None):
            raise ValueError(
                "canonical weapon-enchantment policy resolution requires both runtime source and cadence-family services"
            )
        self.cadence_provider = cadence_provider
        self.effect_family_resolver = (
            effect_family_resolver or self._default_effect_family
        )
        self.runtime_source_service = runtime_source_service
        self.cadence_family_service = cadence_family_service

    @staticmethod
    def _default_effect_family(
        effect: EffectVariant,
    ) -> WeaponEnchantmentEffectFamily | None:
        # Current saved-build enchant EffectVariants expose target buffs/debuffs
        # canonically through SupportEffectCategory. Direct-damage enchant variants
        # do not yet exist in this runtime path, so OTHER/None must not be guessed.
        if effect.category in {
            SupportEffectCategory.BUFF,
            SupportEffectCategory.DEBUFF,
        }:
            return WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF
        return None

    @staticmethod
    def _effect_label(effect: EffectVariant) -> str:
        slot = str(effect.source_slot or "").strip()
        bar = str(
            getattr(effect.active_bar, "value", effect.active_bar) or ""
        ).strip()
        provenance = "/".join(value for value in (bar, slot) if value)
        if provenance:
            return f"{effect.source} [{provenance}]"
        return effect.source

    def resolve(
        self,
        *,
        candidate=None,
        enchantment_effects: tuple[EffectVariant, ...],
        player_build=None,
    ) -> ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolution:
        del candidate  # Signature matches RuntimeScenarioFrontier's resolver seam.

        policies: list[ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy] = []
        evidence: list[str] = []
        unresolved: list[str] = []
        family_by_binding_key: dict[
            tuple[str, str, str, str],
            WeaponEnchantmentEffectFamily,
        ] = {}

        if self.runtime_source_service is not None:
            if player_build is None:
                unresolved.append(
                    "canonical weapon-enchantment cooldown policy resolution requires player_build"
                )
            else:
                source_resolution = self.runtime_source_service.resolve(player_build)
                evidence.extend(tuple(getattr(source_resolution, "evidence", ()) or ()))
                unresolved.extend(tuple(getattr(source_resolution, "unresolved", ()) or ()))
                for source in tuple(getattr(source_resolution, "sources", ()) or ()):
                    family_resolution = self.cadence_family_service.resolve(source)
                    evidence.extend(tuple(family_resolution.evidence))
                    unresolved.extend(tuple(family_resolution.unresolved))
                    if family_resolution.family is None:
                        continue
                    key = (
                        str(source.identity or "").strip().casefold(),
                        str(source.source_label or "").strip().casefold(),
                        str(getattr(source.active_bar, "value", source.active_bar) or "")
                        .strip()
                        .casefold(),
                        str(source.source_slot or "").strip().casefold(),
                    )
                    family_by_binding_key[key] = family_resolution.family

        for effect in tuple(enchantment_effects):
            label = self._effect_label(effect)
            family = (
                family_by_binding_key.get(effect_variant_runtime_binding_key(effect))
                if self.runtime_source_service is not None
                else self.effect_family_resolver(effect)
            )
            if family is None:
                unresolved.append(
                    f"weapon-enchantment effect family is not canonically classified: {label}"
                )
                continue

            cadence = self.cadence_provider(family)
            evidence.extend(
                (
                    f"{label}: cadence family={family.value}",
                    f"{label}: {cadence.cooldown_evidence_note}",
                    f"{label}: {cadence.activation_evidence_note}",
                    f"{label}: {cadence.off_bar_evidence_note}",
                    f"{label}: {cadence.poison_replacement_evidence_note}",
                )
            )

            blockers = tuple(cadence.runtime_blockers)
            if blockers:
                unresolved.extend(
                    f"{label}: {blocker}"
                    for blocker in blockers
                )
                continue

            # runtime_ready proves base cooldown, topology, same-identity sharing,
            # activation semantics, source persistence, and poison replacement.
            # EffectVariant.name is the model's canonical logical identity, so it
            # becomes the cooldown key only after those mechanics are authoritative.
            policies.append(
                ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy(
                    effect=effect,
                    cooldown_identity=effect.name,
                    cooldown_seconds=float(cadence.base_cooldown_seconds),
                    authoritative=True,
                    evidence=(
                        cadence.cooldown_evidence_note,
                        cadence.evidence_note,
                    ),
                )
            )
            evidence.append(
                f"{label}: authoritative cooldown policy "
                f"{effect.name} @ {float(cadence.base_cooldown_seconds):g}s"
            )

        return ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolution(
            policies=tuple(policies),
            evidence=tuple(dict.fromkeys(row for row in evidence if row.strip())),
            unresolved=tuple(
                dict.fromkeys(row for row in unresolved if row.strip())
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolution",
    "ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver",
]
