from __future__ import annotations

"""Resolve the finite weapon-enchantment source-selection frontier.

The caller supplies source-owned candidates plus, when proven, the subset whose
cooldowns are ready at this exact activation opportunity. Update 20 proves that
Dual Wield weapon abilities favor an enchantment that is not on cooldown. The
service therefore narrows to one exact candidate when only one is ready, preserves
finite alternatives when several are ready, and fails closed when a multi-source
choice lacks exact cooldown-state evidence.
"""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from services.extreme_sustained_dps_weapon_enchantment_source_ownership_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceOwnership,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentSourceSelection:
    exact: EffectVariant | None
    alternatives: tuple[EffectVariant, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService:
    """Choose or expose finite alternatives without inventing cooldown state."""

    @staticmethod
    def _candidate_key(effect: EffectVariant) -> tuple[object, ...]:
        return (
            str(effect.name or "").strip().casefold(),
            str(effect.source or "").strip().casefold(),
            str(getattr(effect.active_bar, "value", effect.active_bar) or "")
            .strip()
            .casefold(),
            str(getattr(effect, "source_slot", "") or "").strip().casefold(),
        )

    def resolve(
        self,
        *,
        ownership: ExtremeSustainedDPSWeaponEnchantmentSourceOwnership,
        cooldown_ready: tuple[EffectVariant, ...] | None = None,
    ) -> ExtremeSustainedDPSWeaponEnchantmentSourceSelection:
        if tuple(ownership.unresolved):
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=None,
                alternatives=(),
                unresolved=tuple(ownership.unresolved),
            )

        candidates = tuple(ownership.candidates)
        if not candidates:
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=None,
                alternatives=(),
                evidence=("No source-owned weapon enchantment is available.",),
            )

        if len(candidates) == 1:
            candidate = candidates[0]
            if cooldown_ready is not None:
                ready_keys = {self._candidate_key(effect) for effect in cooldown_ready}
                if self._candidate_key(candidate) not in ready_keys:
                    return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                        exact=None,
                        alternatives=(),
                        evidence=(
                            "The sole source-owned weapon enchantment is proven on cooldown.",
                        ),
                    )
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=candidate,
                alternatives=(candidate,),
                evidence=(
                    "Exactly one source-owned weapon enchantment candidate exists.",
                ),
            )

        if cooldown_ready is None:
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=None,
                alternatives=candidates,
                evidence=(
                    f"Source-owned weapon enchantment candidates: {len(candidates)}",
                    "Update 20 requires cooldown-state-aware preference when Dual Wield has multiple candidates.",
                ),
                unresolved=(
                    "multiple source-owned weapon enchantments require exact cooldown-ready state before source selection",
                ),
            )

        candidate_by_key = {
            self._candidate_key(effect): effect
            for effect in candidates
        }
        ready: list[EffectVariant] = []
        foreign: list[EffectVariant] = []
        for effect in tuple(cooldown_ready):
            key = self._candidate_key(effect)
            candidate = candidate_by_key.get(key)
            if candidate is None:
                foreign.append(effect)
                continue
            if candidate not in ready:
                ready.append(candidate)

        if foreign:
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=None,
                alternatives=(),
                unresolved=(
                    "cooldown-ready evidence contains weapon enchantments outside the source-owned candidate set",
                ),
            )

        if not ready:
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=None,
                alternatives=(),
                evidence=(
                    "All source-owned weapon enchantment candidates are proven on cooldown.",
                ),
            )

        if len(ready) == 1:
            return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
                exact=ready[0],
                alternatives=(ready[0],),
                evidence=(
                    "Exactly one source-owned weapon enchantment is cooldown-ready; Update 20 preference resolves the source.",
                ),
            )

        return ExtremeSustainedDPSWeaponEnchantmentSourceSelection(
            exact=None,
            alternatives=tuple(ready),
            evidence=(
                f"Cooldown-ready source-owned weapon enchantments: {len(ready)}",
                "Multiple ready Dual Wield enchantments remain a finite source-selection frontier.",
            ),
            unresolved=(
                "multiple cooldown-ready weapon enchantments remain source-selection alternatives",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentSourceSelection",
    "ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService",
]
