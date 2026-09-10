from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Protocol

from engine.config import DEFAULT_DATABASE
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.saved_build_adapter import (
    SavedBuildAdaptation,
    SavedBuildCharacterAdapter,
)
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from models.build_model import PlayerBuild
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


class _SavedBuildAdapter(Protocol):
    def adapt(
        self,
        saved: PlayerBuild,
        *,
        character_id: str | None = None,
    ) -> SavedBuildAdaptation: ...


@dataclass(frozen=True)
class RotationHeavyAttackEffectDurationEvidence:
    """Build-effective duration evidence for required heavy-triggered effects."""

    incentives: tuple[HealerHeavyAttackBuildIncentive, ...]
    canonical_build: CharacterBuild | None = None
    unresolved: tuple[str, ...] = ()


class RotationHeavyAttackEffectDurationService:
    """Enrich required heavy incentives through the shared duration authority.

    Heavy-attack discovery owns the source mechanic's recurrence and base/capped
    effect duration. RotationBuildEffectDurationService owns build modifiers such as
    Jorvuld's Guidance. This adapter only connects those contracts; it does not own
    set math, scheduling, recipient coverage, or heavy-attack legality.
    """

    def __init__(
        self,
        duration_service: _DurationService | None = None,
        *,
        database_path: str | Path = DEFAULT_DATABASE,
        build_adapter: _SavedBuildAdapter | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.duration_service = duration_service or RotationBuildEffectDurationService(
            database_path=self.database_path
        )
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(
            self.database_path
        )

    def enrich_saved_build(
        self,
        *,
        build: PlayerBuild,
        incentives: tuple[HealerHeavyAttackBuildIncentive, ...],
        passives: Iterable[PassiveGrant] = (),
        character_id: str | None = None,
    ) -> RotationHeavyAttackEffectDurationEvidence:
        adaptation = self.build_adapter.adapt(build, character_id=character_id)
        adaptation_unresolved = self._dedupe(tuple(adaptation.unresolved))
        if adaptation.build is None:
            details = adaptation_unresolved or (
                "saved-build adaptation returned no canonical CharacterBuild",
            )
            return RotationHeavyAttackEffectDurationEvidence(
                incentives=tuple(incentives),
                canonical_build=None,
                unresolved=details,
            )

        resolved = self.enrich(
            build=adaptation.build,
            incentives=tuple(incentives),
            passives=passives,
        )
        return RotationHeavyAttackEffectDurationEvidence(
            incentives=resolved.incentives,
            canonical_build=adaptation.build,
            unresolved=self._dedupe(
                adaptation_unresolved + tuple(resolved.unresolved)
            ),
        )

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
            canonical_build=build,
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
