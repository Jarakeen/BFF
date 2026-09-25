from __future__ import annotations

"""Authoritative weapon-enchantment cooldown-policy projection for Objective #32.

This service translates canonical EffectVariants into the finite sequence frontier's
cooldown policy shape only when every cadence denominator required by runtime
simulation is authoritative. It intentionally does not infer direct-damage identity
from names, sources, magnitudes, or tooltip text.
"""

from dataclasses import dataclass
import math
from typing import Callable

from minmax.character_build.effect_instance import EffectVariant
from minmax.support_effect_category import SupportEffectCategory
from minmax.runtime_effect_sequence import effect_variant_runtime_binding_key
from minmax.weapon_enchantment_runtime_cadence import (
    WeaponEnchantmentCadenceAuthority,
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
        cooldown_rule_resolver: object | None = None,
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
        self.cooldown_rule_resolver = (
            cooldown_rule_resolver
            or getattr(runtime_source_service, "effect_service", None)
        )

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

    def _resolve_equipped_cooldown(
        self,
        *,
        base_cooldown_seconds: float,
        source,
        label: str,
    ) -> tuple[float | None, tuple[str, ...], tuple[str, ...]]:
        base = float(base_cooldown_seconds)
        trait = str(getattr(source, "weapon_trait", "") or "").strip()
        quality = str(getattr(source, "weapon_quality", "") or "").strip()

        if trait.casefold() == "infused" and not quality:
            return (
                None,
                (),
                (
                    f"{label}: Infused weapon enchantment cooldown requires canonical weapon quality",
                ),
            )

        resolver = self.cooldown_rule_resolver
        if resolver is None:
            if trait.casefold() == "infused":
                return (
                    None,
                    (),
                    (
                        f"{label}: Infused weapon enchantment cooldown requires canonical cooldown-rule resolution",
                    ),
                )
            return base, (f"{label}: no cooldown-modifying weapon trait applies",), ()

        method = getattr(resolver, "resolve_cooldown", None)
        if method is None:
            if trait.casefold() == "infused":
                return (
                    None,
                    (),
                    (
                        f"{label}: cooldown-rule resolver does not expose resolve_cooldown()",
                    ),
                )
            return base, (f"{label}: no reviewed cooldown modifier was required",), ()

        result = method(
            base_cooldown=base,
            weapon_trait=trait or None,
            weapon_quality=quality or None,
        )
        try:
            final = float(getattr(result, "final_cooldown"))
        except (AttributeError, TypeError, ValueError):
            return (
                None,
                (),
                (f"{label}: cooldown-rule resolution returned no numeric final cooldown",),
            )
        if not math.isfinite(final) or final < 0.0:
            return (
                None,
                (),
                (f"{label}: cooldown-rule resolution returned an invalid final cooldown",),
            )

        reduction = getattr(result, "reduction", None)
        reduction_note = ""
        if reduction is not None:
            try:
                numeric_reduction = float(reduction)
            except (TypeError, ValueError):
                return (
                    None,
                    (),
                    (
                        f"{label}: cooldown-rule resolution returned non-numeric reduction evidence",
                    ),
                )
            if not math.isfinite(numeric_reduction):
                return (
                    None,
                    (),
                    (
                        f"{label}: cooldown-rule resolution returned invalid reduction evidence",
                    ),
                )
            reduction_note = f" ({numeric_reduction:g}% reduction)"

        detail = (
            f"{label}: equipped weapon cooldown rules resolved {base:g}s -> {final:g}s"
            + reduction_note
        )
        return final, (detail,), ()

    @staticmethod
    def _candidate_runtime_blockers(
        cadence: WeaponEnchantmentCadenceEvidence,
        *,
        identity_source_count: int,
        distinct_identity_count: int,
    ) -> tuple[str, ...]:
        """Require only cadence facts that can affect this concrete candidate universe."""

        blockers: list[str] = []
        authoritative = WeaponEnchantmentCadenceAuthority.AUTHORITATIVE

        if cadence.base_cooldown_seconds is None:
            blockers.append("base cooldown value is unavailable")
        if cadence.cooldown_authority is not authoritative:
            blockers.append("base cooldown is not authoritative")
        if not cadence.activation_causes:
            blockers.append("activation causes are unavailable")
        if cadence.activation_authority is not authoritative:
            blockers.append("activation causes are not authoritative")
        if cadence.off_bar_source_persists is None:
            blockers.append("off-bar source persistence is unavailable")
        if cadence.off_bar_authority is not authoritative:
            blockers.append("off-bar source persistence is not authoritative")
        if cadence.poison_replaces_enchantment is None:
            blockers.append("poison suppression/replacement rule is unavailable")
        if cadence.poison_replacement_authority is not authoritative:
            blockers.append("poison suppression/replacement rule is not authoritative")

        # Timer-sharing topology is candidate-relative. One physical source has no
        # competing timer. Duplicate copies of one identity require only the explicit
        # same-identity sharing rule. Multiple distinct identities additionally require
        # proof that cooldown identity is scoped per effect identity and that those
        # identities retain independent timers.
        if identity_source_count > 1:
            if cadence.same_effect_identity_shares_cooldown is None:
                blockers.append("same-identity cooldown sharing is unavailable")
            if cadence.same_identity_cooldown_authority is not authoritative:
                blockers.append("same-identity cooldown sharing is not authoritative")

        if distinct_identity_count > 1:
            if not str(cadence.cooldown_scope or "").strip():
                blockers.append("cooldown scope is unavailable")
            if cadence.cooldown_scope_authority is not authoritative:
                blockers.append("cooldown scope is not authoritative")
            if cadence.distinct_effect_identities_have_independent_cooldowns is None:
                blockers.append("distinct-identity cooldown independence is unavailable")
            if cadence.distinct_identity_cooldown_authority is not authoritative:
                blockers.append("distinct-identity cooldown independence is not authoritative")

        return tuple(dict.fromkeys(blockers))

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
        identity_counts: dict[str, int] = {}
        for effect in tuple(enchantment_effects):
            identity_key = str(effect.name or "").strip().casefold()
            if identity_key:
                identity_counts[identity_key] = identity_counts.get(identity_key, 0) + 1
        distinct_identity_count = len(identity_counts)

        family_by_binding_key: dict[
            tuple[str, str, str, str],
            WeaponEnchantmentEffectFamily,
        ] = {}
        source_by_binding_key: dict[
            tuple[str, str, str, str],
            object,
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
                    source_by_binding_key[key] = source

        for effect in tuple(enchantment_effects):
            label = self._effect_label(effect)
            binding_key = effect_variant_runtime_binding_key(effect)
            family = (
                family_by_binding_key.get(binding_key)
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

            identity_key = str(effect.name or "").strip().casefold()
            blockers = self._candidate_runtime_blockers(
                cadence,
                identity_source_count=identity_counts.get(identity_key, 0),
                distinct_identity_count=distinct_identity_count,
            )
            if blockers:
                unresolved.extend(
                    f"{label}: {blocker}"
                    for blocker in blockers
                )
                continue

            # The candidate-scoped gate proves every cadence fact that can actually
            # influence this concrete enchantment universe. It does not require
            # unrelated multi-identity topology for a one-identity candidate.
            # EffectVariant.name is the canonical logical cooldown identity once the
            # relevant sharing/independence rules are authoritative.
            cooldown_seconds = float(cadence.base_cooldown_seconds)
            cooldown_evidence: tuple[str, ...] = ()
            if self.runtime_source_service is not None:
                source = source_by_binding_key.get(binding_key)
                if source is None:
                    unresolved.append(
                        f"{label}: canonical equipped weapon source is unavailable for cooldown-rule resolution"
                    )
                    continue
                (
                    resolved_cooldown,
                    cooldown_evidence,
                    cooldown_unresolved,
                ) = self._resolve_equipped_cooldown(
                    base_cooldown_seconds=cooldown_seconds,
                    source=source,
                    label=label,
                )
                evidence.extend(cooldown_evidence)
                unresolved.extend(cooldown_unresolved)
                if resolved_cooldown is None or cooldown_unresolved:
                    continue
                cooldown_seconds = resolved_cooldown

            policies.append(
                ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy(
                    effect=effect,
                    cooldown_identity=effect.name,
                    cooldown_seconds=cooldown_seconds,
                    authoritative=True,
                    evidence=(
                        cadence.cooldown_evidence_note,
                        cadence.evidence_note,
                        *cooldown_evidence,
                    ),
                )
            )
            evidence.append(
                f"{label}: authoritative cooldown policy "
                f"{effect.name} @ {cooldown_seconds:g}s"
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
