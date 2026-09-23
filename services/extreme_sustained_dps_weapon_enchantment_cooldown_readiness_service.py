from __future__ import annotations

"""Resolve exact weapon-enchantment cooldown readiness from explicit state evidence.

This service owns timestamp arithmetic only. It does not infer weapon-enchantment
base cooldowns, same-identity sharing, cooldown scope, poison suppression, or source
selection. Callers must supply one explicit cooldown-state row for every source-owned
candidate after those mechanics have been resolved elsewhere.
"""

from dataclasses import dataclass
import math

from minmax.character_build.effect_instance import EffectVariant


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentCooldownState:
    effect: EffectVariant
    cooldown_seconds: float
    last_activation_time_seconds: float | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        cooldown = float(self.cooldown_seconds)
        if not math.isfinite(cooldown) or cooldown < 0.0:
            raise ValueError("weapon-enchantment cooldown_seconds must be finite and non-negative")
        object.__setattr__(self, "cooldown_seconds", cooldown)
        if self.last_activation_time_seconds is not None:
            last = float(self.last_activation_time_seconds)
            if not math.isfinite(last) or last < 0.0:
                raise ValueError(
                    "weapon-enchantment last_activation_time_seconds must be finite and non-negative"
                )
            object.__setattr__(self, "last_activation_time_seconds", last)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness:
    ready: tuple[EffectVariant, ...]
    blocked: tuple[EffectVariant, ...]
    ready_at: tuple[tuple[EffectVariant, float], ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService:
    """Evaluate exact readiness without inventing cooldown topology."""

    @staticmethod
    def _effect_key(effect: EffectVariant) -> tuple[str, str, str, str]:
        return (
            str(effect.name or "").strip().casefold(),
            str(effect.source or "").strip().casefold(),
            str(getattr(effect.active_bar, "value", effect.active_bar) or "")
            .strip()
            .casefold(),
            str(getattr(effect, "source_slot", "") or "").strip().casefold(),
        )

    @classmethod
    def resolve(
        cls,
        *,
        activation_time_seconds: float,
        candidates: tuple[EffectVariant, ...],
        states: tuple[ExtremeSustainedDPSWeaponEnchantmentCooldownState, ...],
    ) -> ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness:
        now = float(activation_time_seconds)
        if not math.isfinite(now) or now < 0.0:
            raise ValueError(
                "weapon-enchantment activation_time_seconds must be finite and non-negative"
            )

        candidate_by_key = {cls._effect_key(effect): effect for effect in candidates}
        if len(candidate_by_key) != len(tuple(candidates)):
            return ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness(
                ready=(),
                blocked=(),
                ready_at=(),
                unresolved=(
                    "source-owned weapon-enchantment candidates are not uniquely identifiable by identity/source/bar/slot",
                ),
            )

        state_by_key: dict[
            tuple[str, str, str, str],
            ExtremeSustainedDPSWeaponEnchantmentCooldownState,
        ] = {}
        foreign: list[ExtremeSustainedDPSWeaponEnchantmentCooldownState] = []
        duplicates: list[tuple[str, str, str, str]] = []
        for state in tuple(states):
            key = cls._effect_key(state.effect)
            if key not in candidate_by_key:
                foreign.append(state)
                continue
            if key in state_by_key:
                duplicates.append(key)
                continue
            state_by_key[key] = state

        unresolved: list[str] = []
        if foreign:
            unresolved.append(
                "cooldown-state evidence contains weapon enchantments outside the source-owned candidate set"
            )
        if duplicates:
            unresolved.append(
                "duplicate cooldown-state evidence exists for a source-owned weapon enchantment"
            )

        missing = tuple(
            effect
            for key, effect in candidate_by_key.items()
            if key not in state_by_key
        )
        if missing:
            unresolved.append(
                "exact cooldown-state evidence is missing for one or more source-owned weapon enchantments"
            )

        if unresolved:
            return ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness(
                ready=(),
                blocked=(),
                ready_at=(),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        ready: list[EffectVariant] = []
        blocked: list[EffectVariant] = []
        ready_at: list[tuple[EffectVariant, float]] = []
        evidence: list[str] = []
        for effect in tuple(candidates):
            state = state_by_key[cls._effect_key(effect)]
            last = state.last_activation_time_seconds
            if last is None:
                ready.append(effect)
                ready_at.append((effect, 0.0))
                evidence.extend(state.evidence)
                continue

            available_at = last + state.cooldown_seconds
            ready_at.append((effect, available_at))
            evidence.extend(state.evidence)
            if now + 1e-12 >= available_at:
                ready.append(effect)
            else:
                blocked.append(effect)

        return ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness(
            ready=tuple(ready),
            blocked=tuple(blocked),
            ready_at=tuple(ready_at),
            evidence=tuple(
                dict.fromkeys(
                    (
                        *evidence,
                        f"Weapon-enchantment cooldown state rows resolved: {len(states)}",
                        f"Cooldown-ready candidates at {now:g}s: {len(ready)}",
                        f"Cooldown-blocked candidates at {now:g}s: {len(blocked)}",
                        "Cooldown arithmetic consumes explicit per-candidate state and does not infer shared-identity cooldown topology.",
                    )
                )
            ),
            unresolved=(),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness",
    "ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService",
    "ExtremeSustainedDPSWeaponEnchantmentCooldownState",
]
