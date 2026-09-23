from __future__ import annotations

"""Bind one fully resolved weapon-enchantment activation to runtime history."""

from dataclasses import dataclass

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_sustained_dps_weapon_enchantment_activation_resolution_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationResolution,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentAttemptBinding:
    attempt: RuntimeEffectEventAttempt | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService:
    """Create one source-bound runtime attempt only when proc truth is proven."""

    @classmethod
    def bind(
        cls,
        resolution: ExtremeSustainedDPSWeaponEnchantmentActivationResolution,
        *,
        chance_roll: float | None = None,
        condition_context=None,
    ) -> ExtremeSustainedDPSWeaponEnchantmentAttemptBinding:
        if tuple(resolution.unresolved):
            return ExtremeSustainedDPSWeaponEnchantmentAttemptBinding(
                attempt=None,
                evidence=tuple(resolution.evidence),
                unresolved=tuple(resolution.unresolved),
            )

        proc_occurs = resolution.proc_occurs
        if proc_occurs is None:
            return ExtremeSustainedDPSWeaponEnchantmentAttemptBinding(
                attempt=None,
                evidence=tuple(resolution.evidence),
                unresolved=(
                    "weapon-enchantment runtime attempt requires proven cooldown readiness before proc binding",
                ),
            )

        if proc_occurs is False:
            return ExtremeSustainedDPSWeaponEnchantmentAttemptBinding(
                attempt=None,
                evidence=(
                    *tuple(resolution.evidence),
                    "Weapon-enchantment activation opportunity produced no proc.",
                ),
            )

        effect = resolution.exact
        if effect is None:
            return ExtremeSustainedDPSWeaponEnchantmentAttemptBinding(
                attempt=None,
                evidence=tuple(resolution.evidence),
                unresolved=(
                    "weapon-enchantment proc is proven but exact source selection is unresolved",
                ),
            )

        return ExtremeSustainedDPSWeaponEnchantmentAttemptBinding(
            attempt=RuntimeEffectEventAttempt.for_bound_effect(
                event=resolution.activation_event,
                effect=effect,
                chance_roll=chance_roll,
                condition_context=condition_context,
            ),
            evidence=(
                *tuple(resolution.evidence),
                f"Weapon-enchantment runtime attempt bound to {effect.source}.",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentAttemptBinding",
    "ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService",
]
