from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_availability import (
    resolve_available_effects,
    resolve_ultimate_cast_effects,
)
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_build_effect_duration_service import RotationBuildEffectDurationService


_TEMPORAL_LAYERS = frozenset(
    {
        EffectLayer.PROC,
        EffectLayer.ULTIMATE,
        EffectLayer.CONSUMABLE,
    }
)


@dataclass(frozen=True)
class RotationTemporalEffectRequirement:
    """Minimum uptime for one explicitly activated non-cast effect."""

    effect_name: str
    layer: EffectLayer
    minimum_uptime: float
    source: str

    def __post_init__(self) -> None:
        effect_name = str(self.effect_name or "").strip()
        source = str(self.source or "").strip()
        if not effect_name:
            raise ValueError("rotation temporal effect requirement needs effect_name")
        if not source:
            raise ValueError("rotation temporal effect requirement needs source")
        if self.layer not in _TEMPORAL_LAYERS:
            raise ValueError(
                "rotation temporal effect requirement only supports proc, ultimate, or consumable layers"
            )
        minimum = float(self.minimum_uptime)
        if not math.isfinite(minimum) or not 0.0 <= minimum <= 1.0:
            raise ValueError("rotation temporal effect minimum_uptime must be between 0 and 1")
        object.__setattr__(self, "effect_name", effect_name)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "minimum_uptime", minimum)


@dataclass(frozen=True)
class RotationTemporalEffectApplication:
    """Evidence that one temporal effect actually activated at one time/bar.

    ``sequence`` is optional ordering evidence within a shared timestamp. It uses
    the same ordering domain as ``RotationAction.sequence``. When absent, callers
    retain the older conservative behavior: a same-timestamp bar swap cannot be
    ordered relative to this activation and plan legality remains unresolved.
    """

    time_seconds: float
    effect_name: str
    layer: EffectLayer
    source: str
    bar: str
    trigger: str | None = None
    sequence: int | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not math.isfinite(time_seconds) or time_seconds < 0.0:
            raise ValueError("rotation temporal effect application time must be finite and non-negative")
        effect_name = str(self.effect_name or "").strip()
        source = str(self.source or "").strip()
        bar = str(self.bar or "").strip().casefold()
        if not effect_name:
            raise ValueError("rotation temporal effect application needs effect_name")
        if not source:
            raise ValueError("rotation temporal effect application needs source")
        if self.layer not in _TEMPORAL_LAYERS:
            raise ValueError(
                "rotation temporal effect application only supports proc, ultimate, or consumable layers"
            )
        if bar not in {"front", "back"}:
            raise ValueError("rotation temporal effect application bar must be front or back")
        if self.sequence is not None:
            sequence = int(self.sequence)
            if sequence < 0 or sequence != self.sequence:
                raise ValueError("rotation temporal effect application sequence must be a non-negative integer")
            object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "effect_name", effect_name)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationTemporalEffectSummary:
    requirement: RotationTemporalEffectRequirement
    application_count: int
    active_seconds: float
    uptime_fraction: float
    effective_durations: tuple[float, ...]
    applied_modifier_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationTemporalEffectAssessment:
    requirement: RotationTemporalEffectRequirement
    summary: RotationTemporalEffectSummary | None
    unresolved: tuple[str, ...] = ()

    @property
    def observed_uptime(self) -> float | None:
        return None if self.summary is None else self.summary.uptime_fraction

    @property
    def shortfall(self) -> float | None:
        if self.observed_uptime is None:
            return None
        return max(0.0, self.requirement.minimum_uptime - self.observed_uptime)

    @property
    def satisfied(self) -> bool:
        return self.shortfall == 0.0


class RotationTemporalEffectUptimeService:
    """Measure runtime coverage from explicit proc/ultimate/consumable activations.

    This service never invents activations from proc chance, cooldown, tooltip text,
    or merely having an effect available on the build. An activation must be supplied
    explicitly. The exact build/bar effect is then resolved and its build-effective
    duration is used for coverage.
    """

    def __init__(
        self,
        duration_service: RotationBuildEffectDurationService | None = None,
    ) -> None:
        self.duration_service = duration_service or RotationBuildEffectDurationService()

    def assess(
        self,
        *,
        duration_seconds: float,
        build: CharacterBuild,
        requirements: tuple[RotationTemporalEffectRequirement, ...],
        applications: tuple[RotationTemporalEffectApplication, ...] = (),
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationTemporalEffectAssessment, ...]:
        duration = float(duration_seconds)
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError("rotation temporal effect assessment duration must be positive")

        seen: set[tuple[str, EffectLayer, str]] = set()
        passive_tuple = tuple(passives)
        assessments: list[RotationTemporalEffectAssessment] = []
        for requirement in requirements:
            key = (
                requirement.effect_name.casefold(),
                requirement.layer,
                requirement.source.casefold(),
            )
            if key in seen:
                raise ValueError(
                    "duplicate rotation temporal effect requirement for "
                    f"{requirement.effect_name!r} from {requirement.source!r}"
                )
            seen.add(key)
            matching = tuple(
                application
                for application in applications
                if application.effect_name.casefold() == requirement.effect_name.casefold()
                and application.layer == requirement.layer
                and application.source.casefold() == requirement.source.casefold()
            )
            assessments.append(
                self._assess_one(
                    duration_seconds=duration,
                    build=build,
                    requirement=requirement,
                    applications=matching,
                    passives=passive_tuple,
                )
            )
        return tuple(assessments)

    def _assess_one(
        self,
        *,
        duration_seconds: float,
        build: CharacterBuild,
        requirement: RotationTemporalEffectRequirement,
        applications: tuple[RotationTemporalEffectApplication, ...],
        passives: tuple[PassiveGrant, ...],
    ) -> RotationTemporalEffectAssessment:
        if not applications:
            return RotationTemporalEffectAssessment(
                requirement=requirement,
                summary=RotationTemporalEffectSummary(
                    requirement=requirement,
                    application_count=0,
                    active_seconds=0.0,
                    uptime_fraction=0.0,
                    effective_durations=(),
                ),
            )

        intervals: list[tuple[float, float]] = []
        durations: list[float] = []
        modifier_sources: list[str] = []
        unresolved: list[str] = []
        for application in applications:
            if application.time_seconds >= duration_seconds:
                continue
            bar_id = BarId(application.bar)
            matches = self._resolve_effect_matches(
                build=build,
                application=application,
                active_bar=bar_id,
                passives=passives,
            )
            if len(matches) != 1:
                if not matches:
                    unresolved.append(
                        f"no exact {application.layer.value} effect {application.effect_name!r} "
                        f"from {application.source!r} resolved on {application.bar} bar"
                    )
                else:
                    unresolved.append(
                        f"multiple exact {application.layer.value} effect variants resolved for "
                        f"{application.effect_name!r} from {application.source!r} on {application.bar} bar"
                    )
                continue

            effect = matches[0]
            resolution = self.duration_service.resolve(
                build=build,
                active_bar=bar_id,
                effect=effect,
                passives=passives,
            )
            if resolution.effective_duration_seconds is None:
                unresolved.extend(
                    resolution.unresolved
                    or (
                        f"effective duration unresolved for {application.effect_name!r} "
                        f"from {application.source!r}",
                    )
                )
                continue

            effect_duration = float(resolution.effective_duration_seconds)
            durations.append(effect_duration)
            intervals.append(
                (
                    application.time_seconds,
                    min(duration_seconds, application.time_seconds + effect_duration),
                )
            )
            for modifier in resolution.applied_modifiers:
                if modifier.source not in modifier_sources:
                    modifier_sources.append(modifier.source)

        if unresolved:
            return RotationTemporalEffectAssessment(
                requirement=requirement,
                summary=None,
                unresolved=self._dedupe(tuple(unresolved)),
            )

        active_seconds = self._union_seconds(tuple(intervals))
        return RotationTemporalEffectAssessment(
            requirement=requirement,
            summary=RotationTemporalEffectSummary(
                requirement=requirement,
                application_count=len(intervals),
                active_seconds=active_seconds,
                uptime_fraction=active_seconds / duration_seconds,
                effective_durations=tuple(durations),
                applied_modifier_sources=tuple(modifier_sources),
            ),
        )

    @staticmethod
    def _resolve_effect_matches(
        *,
        build: CharacterBuild,
        application: RotationTemporalEffectApplication,
        active_bar: BarId,
        passives: tuple[PassiveGrant, ...],
    ) -> tuple[EffectVariant, ...]:
        if application.layer == EffectLayer.ULTIMATE:
            candidates = resolve_ultimate_cast_effects(
                build,
                active_bar,
                trigger=application.trigger,
            )
        else:
            candidates = resolve_available_effects(build, active_bar, passives)

        return tuple(
            effect
            for effect in candidates
            if effect.name.casefold() == application.effect_name.casefold()
            and effect.layer == application.layer
            and effect.source.casefold() == application.source.casefold()
        )

    @staticmethod
    def _union_seconds(intervals: tuple[tuple[float, float], ...]) -> float:
        if not intervals:
            return 0.0
        ordered = sorted(intervals)
        total = 0.0
        start, end = ordered[0]
        for next_start, next_end in ordered[1:]:
            if next_start <= end:
                end = max(end, next_end)
                continue
            total += max(0.0, end - start)
            start, end = next_start, next_end
        total += max(0.0, end - start)
        return total

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationTemporalEffectApplication",
    "RotationTemporalEffectAssessment",
    "RotationTemporalEffectRequirement",
    "RotationTemporalEffectSummary",
    "RotationTemporalEffectUptimeService",
]
