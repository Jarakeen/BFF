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
    cooldown_state_proven: bool = False
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.exact is not None and not isinstance(self.exact, EffectVariant):
            raise TypeError("weapon-enchantment activation exact source must be EffectVariant")
        if not isinstance(self.alternatives, tuple):
            raise TypeError("weapon-enchantment activation alternatives must be a tuple")
        if any(not isinstance(row, EffectVariant) for row in self.alternatives):
            raise TypeError(
                "weapon-enchantment activation alternatives must contain EffectVariant records"
            )
        if not isinstance(self.cooldown_state_proven, bool):
            raise TypeError(
                "weapon-enchantment activation cooldown_state_proven must be boolean"
            )
        if not isinstance(self.evidence, tuple):
            raise TypeError("weapon-enchantment activation evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("weapon-enchantment activation unresolved must be a tuple")
        if any(not isinstance(row, str) for row in self.evidence):
            raise TypeError("weapon-enchantment activation evidence must contain strings")
        if any(not isinstance(row, str) for row in self.unresolved):
            raise TypeError("weapon-enchantment activation unresolved must contain strings")

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    @property
    def proc_occurs(self) -> bool | None:
        if self.unresolved:
            return None
        if self.exact is None and not self.alternatives:
            return False
        if not self.cooldown_state_proven:
            return None
        return True


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
        if not isinstance(enchantment_effects, tuple):
            raise TypeError("weapon-enchantment activation enchantment_effects must be a tuple")
        if any(not isinstance(row, EffectVariant) for row in enchantment_effects):
            raise TypeError(
                "weapon-enchantment activation enchantment_effects must contain EffectVariant records"
            )
        if cooldown_ready is not None:
            if not isinstance(cooldown_ready, tuple):
                raise TypeError("weapon-enchantment activation cooldown_ready must be a tuple")
            if any(not isinstance(row, EffectVariant) for row in cooldown_ready):
                raise TypeError(
                    "weapon-enchantment activation cooldown_ready must contain EffectVariant records"
                )
        if cooldown_states is not None:
            if not isinstance(cooldown_states, tuple):
                raise TypeError("weapon-enchantment activation cooldown_states must be a tuple")
            if any(
                not isinstance(row, ExtremeSustainedDPSWeaponEnchantmentCooldownState)
                for row in cooldown_states
            ):
                raise TypeError(
                    "weapon-enchantment activation cooldown_states must contain canonical cooldown-state records"
                )

        trigger = getattr(activation_event, "trigger", "")
        if not isinstance(trigger, str):
            raise TypeError("weapon-enchantment activation event trigger must be a string")
        trigger = trigger.strip()
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
            enchantment_effects=enchantment_effects,
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

        cooldown_state_proven = cooldown_ready is not None or cooldown_states is not None
        readiness_evidence: tuple[str, ...] = ()
        if cooldown_states is not None:
            activation_time = getattr(activation_event, "time_seconds", None)
            if isinstance(activation_time, bool) or not isinstance(
                activation_time,
                (int, float),
            ):
                raise TypeError(
                    "weapon-enchantment activation event time_seconds must be numeric"
                )
            readiness = self.readiness_service.resolve(
                activation_time_seconds=float(activation_time),
                candidates=tuple(ownership.candidates),
                states=cooldown_states,
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
            cooldown_state_proven=cooldown_state_proven,
            evidence=evidence,
            unresolved=tuple(selection.unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentActivationResolution",
    "ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService",
]
