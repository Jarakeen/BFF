from __future__ import annotations

"""Compose one exact weapon-enchantment activation source decision.

This service does not infer cooldown cadence or sharing topology. It joins the
authoritative activation event/source-bar provenance with source-owned enchantment
variants and either a caller-proven cooldown-ready subset or explicit per-candidate
cooldown-state rows. The result is one exact proc source, a finite unresolved
alternative set, or no proc source when every owned candidate is proven unavailable.
"""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
)
from services.extreme_sustained_dps_weapon_enchantment_cooldown_readiness_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService,
    ExtremeSustainedDPSWeaponEnchantmentCooldownState,
)
from services.extreme_sustained_dps_weapon_enchantment_source_ownership_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService,
)
from services.extreme_sustained_dps_weapon_enchantment_source_selection_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentActivationResolution:
    activation_event: object
    exact: EffectVariant | None
    alternatives: tuple[EffectVariant, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    @property
    def proc_occurs(self) -> bool | None:
        if self.unresolved:
            return None
        return self.exact is not None or bool(self.alternatives)


class ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService:
    """Resolve source ownership and one-hit source selection as one contract."""

    def __init__(
        self,
        *,
        ownership_service: object | None = None,
        readiness_service: object | None = None,
        selection_service: object | None = None,
    ) -> None:
        self.ownership_service = (
            ownership_service
            or ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService()
        )
        self.readiness_service = (
            readiness_service
            or ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService()
        )
        self.selection_service = (
            selection_service
            or ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService()
        )

    def resolve(
        self,
        *,
        activation_event: object,
        enchantment_effects: tuple[EffectVariant, ...],
        cooldown_ready: tuple[EffectVariant, ...] | None = None,
        cooldown_states: tuple[
            ExtremeSustainedDPSWeaponEnchantmentCooldownState, ...
        ] | None = None,
    ) -> ExtremeSustainedDPSWeaponEnchantmentActivationResolution:
        trigger = str(getattr(activation_event, "trigger", "") or "").strip()
        if trigger != WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER:
            return ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
                activation_event=activation_event,
                exact=None,
                alternatives=(),
                unresolved=(
                    "weapon-enchantment activation resolution requires a canonical weapon_enchantment_activation event",
                ),
            )

        ownership = self.ownership_service.resolve(
            activation_event=activation_event,
            enchantment_effects=tuple(enchantment_effects),
        )
        if tuple(ownership.unresolved):
            return ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
                activation_event=activation_event,
                exact=None,
                alternatives=(),
                evidence=tuple(ownership.evidence),
                unresolved=tuple(ownership.unresolved),
            )

        if cooldown_ready is not None and cooldown_states is not None:
            raise ValueError(
                "weapon-enchantment activation resolution accepts cooldown_ready or cooldown_states, not both"
            )

        readiness_evidence: tuple[str, ...] = ()
        if cooldown_states is not None:
            readiness = self.readiness_service.resolve(
                activation_time_seconds=float(
                    getattr(activation_event, "time_seconds")
                ),
                candidates=tuple(ownership.candidates),
                states=tuple(cooldown_states),
            )
            if tuple(readiness.unresolved):
                return ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
                    activation_event=activation_event,
                    exact=None,
                    alternatives=(),
                    evidence=(
                        *tuple(ownership.evidence),
                        *tuple(readiness.evidence),
                    ),
                    unresolved=tuple(readiness.unresolved),
                )
            cooldown_ready = tuple(readiness.ready)
            readiness_evidence = tuple(readiness.evidence)

        selection = self.selection_service.resolve(
            ownership=ownership,
            cooldown_ready=cooldown_ready,
        )
        evidence = tuple(
            dict.fromkeys(
                (
                    *tuple(ownership.evidence),
                    *readiness_evidence,
                    *tuple(selection.evidence),
                    "One isolated damage occurrence may resolve at most one weapon-enchantment source.",
                )
            )
        )
        return ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
            activation_event=activation_event,
            exact=selection.exact,
            alternatives=tuple(selection.alternatives),
            evidence=evidence,
            unresolved=tuple(selection.unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentActivationResolution",
    "ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService",
]
