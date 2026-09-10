from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Protocol

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from services.rotation_build_effect_duration_service import RotationBuildEffectDurationService


class _DurationService(Protocol):
    def resolve(
        self,
        *,
        build: CharacterBuild,
        active_bar: BarId,
        effect: EffectVariant,
        passives: Iterable[PassiveGrant] = (),
    ): ...


@dataclass(frozen=True)
class RotationHeavyAttackEffectDurationEvidence:
    """Build-effective duration evidence for required heavy-triggered effects."""

    incentives: tuple[HealerHeavyAttackBuildIncentive, ...]
    unresolved: tuple[str, ...] = ()


class RotationHeavyAttackEffectDurationService:
    """Enrich required heavy incentives through the shared duration authority.

    Heavy-attack discovery owns the source mechanic's recurrence and base/capped
    effect duration. RotationBuildEffectDurationService owns build modifiers such as
    Jorvuld's Guidance. This adapter only connects those contracts; it does not own
    set math, scheduling, recipient coverage, or heavy-attack legality.
    """

    def __init__(self, duration_service: _DurationService | None = None) -> None:
        self.duration_service = duration_service or RotationBuildEffectDurationService()

    def enrich(
        self,
        *,
        build: CharacterBuild,
        incentives: tuple[HealerHeavyAttackBuildIncentive, ...],
        passives: Iterable[PassiveGrant] = (),
    ) -> RotationHeavyAttackEffectDurationEvidence:
        enriched: list[HealerHeavyAttackBuildIncentive] = []
        unresolved: list[str] = []
        passive_tuple = tuple(passives)

        for incentive in incentives:
            if incentive.kind is not HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT:
                enriched.append(incentive)
                continue

            if incentive.maximum_effect_duration_seconds is None:
                enriched.append(incentive)
                continue

            if not incentive.required_effect_name or incentive.required_effect_category is None:
                unresolved.append(
                    f"{incentive.name}: required heavy effect identity/category unresolved"
                )
                enriched.append(incentive)
                continue

            active_bar = BarId.FRONT if incentive.bar == "front" else BarId.BACK
            effect = EffectVariant(
                name=incentive.required_effect_name,
                layer=EffectLayer.PROC,
                source=incentive.name,
                duration=float(incentive.maximum_effect_duration_seconds),
                category=incentive.required_effect_category,
            )
            resolution = self.duration_service.resolve(
                build=build,
                active_bar=active_bar,
                effect=effect,
                passives=passive_tuple,
            )
            if resolution.unresolved or resolution.effective_duration_seconds is None:
                unresolved.extend(
                    resolution.unresolved
                    or (
                        f"{incentive.name}: build-effective required effect duration unresolved",
                    )
                )
                enriched.append(incentive)
                continue

            enriched.append(
                replace(
                    incentive,
                    effective_effect_duration_seconds=float(
                        resolution.effective_duration_seconds
                    ),
                )
            )

        return RotationHeavyAttackEffectDurationEvidence(
            incentives=tuple(enriched),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = [
    "RotationHeavyAttackEffectDurationEvidence",
    "RotationHeavyAttackEffectDurationService",
]
