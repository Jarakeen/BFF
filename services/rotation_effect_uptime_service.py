from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math
import re

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_build_effect_duration_service import RotationBuildEffectDurationService


@dataclass(frozen=True)
class RotationEffectUptimeRequirement:
    """Explicit minimum runtime coverage for one cast-produced build effect.

    ``source_skill_name`` identifies the scheduled skill that produces the effect;
    ``effect_name`` is the canonical EffectVariant identity. The two are kept
    separate because skill uptime and effect uptime are not mechanically
    interchangeable in ESO.
    """

    effect_name: str
    source_skill_name: str
    minimum_uptime: float
    bar: str | None = None

    def __post_init__(self) -> None:
        effect_name = str(self.effect_name or "").strip()
        source_skill_name = str(self.source_skill_name or "").strip()
        if not effect_name:
            raise ValueError("rotation effect uptime requirement needs effect_name")
        if not source_skill_name:
            raise ValueError("rotation effect uptime requirement needs source_skill_name")
        object.__setattr__(self, "effect_name", effect_name)
        object.__setattr__(self, "source_skill_name", source_skill_name)

        minimum = float(self.minimum_uptime)
        if not math.isfinite(minimum) or not 0.0 <= minimum <= 1.0:
            raise ValueError("rotation effect uptime minimum must be finite and between 0 and 1")
        object.__setattr__(self, "minimum_uptime", minimum)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation effect uptime bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationEffectUptimeSummary:
    effect_name: str
    source_skill_name: str
    bar: str
    base_duration_seconds: float
    effective_duration_seconds: float
    cast_count: int
    active_seconds: float
    uptime_fraction: float
    applied_modifier_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationEffectUptimeAssessment:
    requirement: RotationEffectUptimeRequirement
    summary: RotationEffectUptimeSummary | None
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


class RotationEffectUptimeService:
    """Measure build-effective runtime coverage for cast-produced effects.

    Resolution is deterministic and evidence preserving:
    - source skills are matched by canonical stable identity, never fuzzy text;
    - the requested effect must exist on that exact slotted skill;
    - only CAST/ULTIMATE effect layers are treated as produced by scheduled casts;
    - build-aware effect duration is delegated to the canonical effect resolver;
    - overlapping applications are unioned rather than double-counted.

    Proc-trigger, passive, slotted, aura, and target-state coverage require their
    own temporal evidence and are intentionally not inferred from skill casts here.
    """

    def __init__(
        self,
        duration_service: RotationBuildEffectDurationService | None = None,
    ) -> None:
        self.duration_service = duration_service or RotationBuildEffectDurationService()

    def assess(
        self,
        *,
        plan: RotationPlan,
        build: CharacterBuild,
        requirements: tuple[RotationEffectUptimeRequirement, ...],
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationEffectUptimeAssessment, ...]:
        seen: set[tuple[str, str, str | None]] = set()
        assessments: list[RotationEffectUptimeAssessment] = []
        passive_tuple = tuple(passives)

        for requirement in requirements:
            key = (
                requirement.effect_name.casefold(),
                self._stable_skill_id(requirement.source_skill_name),
                requirement.bar,
            )
            if key in seen:
                raise ValueError(
                    "duplicate rotation effect uptime requirement for "
                    f"{requirement.effect_name!r} from {requirement.source_skill_name!r}"
                )
            seen.add(key)
            assessments.append(
                self._assess_one(
                    plan=plan,
                    build=build,
                    requirement=requirement,
                    passives=passive_tuple,
                )
            )
        return tuple(assessments)

    def _assess_one(
        self,
        *,
        plan: RotationPlan,
        build: CharacterBuild,
        requirement: RotationEffectUptimeRequirement,
        passives: tuple[PassiveGrant, ...],
    ) -> RotationEffectUptimeAssessment:
        source_id = self._stable_skill_id(requirement.source_skill_name)
        candidate_slots: list[tuple[BarId, object]] = []
        for bar in build.bars():
            if requirement.bar is not None and bar.bar_id.value != requirement.bar:
                continue
            for slot in bar.slots:
                if self._stable_skill_id(slot.skill_id) == source_id:
                    candidate_slots.append((bar.bar_id, slot))

        if not candidate_slots:
            scope = f" on {requirement.bar} bar" if requirement.bar else ""
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(
                    f"source skill {requirement.source_skill_name!r}{scope} is not slotted",
                ),
            )
        if len(candidate_slots) > 1 and requirement.bar is None:
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(
                    f"source skill {requirement.source_skill_name!r} is ambiguous across bars",
                ),
            )
        if len(candidate_slots) > 1:
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(
                    f"source skill {requirement.source_skill_name!r} appears more than once "
                    f"on {requirement.bar} bar",
                ),
            )

        bar_id, slot = candidate_slots[0]
        effect_matches = tuple(
            effect
            for effect in slot.effects
            if effect.name.casefold() == requirement.effect_name.casefold()
            and effect.layer in {EffectLayer.CAST, EffectLayer.ULTIMATE}
        )
        if not effect_matches:
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(
                    f"effect {requirement.effect_name!r} is not a verified cast-produced "
                    f"effect of {requirement.source_skill_name!r} on {bar_id.value} bar",
                ),
            )
        if len(effect_matches) > 1:
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(
                    f"effect {requirement.effect_name!r} from "
                    f"{requirement.source_skill_name!r} has multiple cast variants",
                ),
            )

        effect: EffectVariant = effect_matches[0]
        duration = self.duration_service.resolve(
            build=build,
            active_bar=bar_id,
            effect=effect,
            passives=passives,
        )
        if duration.effective_duration_seconds is None or duration.base_duration_seconds is None:
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=duration.unresolved
                or (
                    f"effective duration unresolved for effect {requirement.effect_name!r}",
                ),
            )

        matching_named_actions = tuple(
            action
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and action.name is not None
            and self._stable_skill_id(action.name) == source_id
        )
        if any(action.bar is None for action in matching_named_actions):
            return RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(
                    f"scheduled casts of {requirement.source_skill_name!r} need explicit bar evidence",
                ),
            )

        cast_times = tuple(
            action.time_seconds
            for action in matching_named_actions
            if action.bar == bar_id.value
        )
        intervals = tuple(
            (
                time_seconds,
                min(plan.duration_seconds, time_seconds + duration.effective_duration_seconds),
            )
            for time_seconds in cast_times
            if time_seconds < plan.duration_seconds
        )
        active_seconds = self._union_seconds(intervals)
        uptime = (
            active_seconds / plan.duration_seconds
            if plan.duration_seconds > 0.0
            else 0.0
        )
        summary = RotationEffectUptimeSummary(
            effect_name=effect.name,
            source_skill_name=requirement.source_skill_name,
            bar=bar_id.value,
            base_duration_seconds=duration.base_duration_seconds,
            effective_duration_seconds=duration.effective_duration_seconds,
            cast_count=len(cast_times),
            active_seconds=active_seconds,
            uptime_fraction=uptime,
            applied_modifier_sources=tuple(
                modifier.source for modifier in duration.applied_modifiers
            ),
        )
        return RotationEffectUptimeAssessment(
            requirement=requirement,
            summary=summary,
        )

    @staticmethod
    def _stable_skill_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

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


__all__ = [
    "RotationEffectUptimeAssessment",
    "RotationEffectUptimeRequirement",
    "RotationEffectUptimeService",
    "RotationEffectUptimeSummary",
]
