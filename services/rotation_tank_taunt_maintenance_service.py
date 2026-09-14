from __future__ import annotations

"""Assess continuous target-specific taunt maintenance from canonical duration evidence.

This layer answers one narrow question: does the scheduled plan keep one explicitly
named encounter target continuously taunted for a reviewed responsibility window?

Canonical taunt duration comes from RotationTankTauntDurationService. The requirement
owns target identity and the exact active window. This service deliberately does not
invent refresh lead, recast cadence, overtaunt/immunity behavior, or target swaps.
Those remain separate strategy/runtime evidence.
"""

from dataclasses import dataclass
import math
from pathlib import Path

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleHardObligationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_duration_service import (
    RotationTankTauntDurationResolution,
    RotationTankTauntDurationService,
)


@dataclass(frozen=True)
class RotationTankTauntMaintenanceRequirement:
    requirement_id: str
    source_skill_name: str
    target_key: str
    active_start_seconds: float
    active_end_seconds: float
    bar: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        requirement_id = str(self.requirement_id or "").strip()
        source_skill_name = str(self.source_skill_name or "").strip()
        target_key = str(self.target_key or "").strip()
        if not requirement_id:
            raise ValueError("tank taunt maintenance requires requirement_id")
        if not source_skill_name:
            raise ValueError("tank taunt maintenance requires source_skill_name")
        if not target_key:
            raise ValueError("tank taunt maintenance requires explicit target_key")
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "source_skill_name", source_skill_name)
        object.__setattr__(self, "target_key", target_key)

        start = float(self.active_start_seconds)
        end = float(self.active_end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("tank taunt maintenance start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("tank taunt maintenance end must be finite and greater than start")
        object.__setattr__(self, "active_start_seconds", start)
        object.__setattr__(self, "active_end_seconds", end)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank taunt maintenance bar must be front or back")
            object.__setattr__(self, "bar", bar)

        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.provenance
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class RotationTankTauntMaintenanceInterval:
    cast_time_seconds: float
    active_start_seconds: float
    active_end_seconds: float
    bar: str | None
    target_key: str


@dataclass(frozen=True)
class RotationTankTauntMaintenanceAssessment:
    requirement: RotationTankTauntMaintenanceRequirement
    duration_seconds: float | None
    matching_casts: tuple[RotationAction, ...]
    active_intervals: tuple[RotationTankTauntMaintenanceInterval, ...]
    uncovered_windows: tuple[tuple[float, float], ...]
    required_seconds: float
    covered_seconds: float
    resolved: bool
    satisfied: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationTankTauntMaintenanceService:
    """Measure continuous taunt coverage for one explicit target responsibility."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        duration_service: RotationTankTauntDurationService | object | None = None,
    ) -> None:
        self.duration_service = duration_service or RotationTankTauntDurationService(
            database_path
        )

    def assess(
        self,
        *,
        plan: RotationPlan,
        requirement: RotationTankTauntMaintenanceRequirement,
    ) -> RotationTankTauntMaintenanceAssessment:
        duration_resolution = self.duration_service.resolve(requirement.source_skill_name)
        if not bool(getattr(duration_resolution, "resolved", False)):
            messages = tuple(getattr(duration_resolution, "unresolved", ())) or (
                f"{requirement.source_skill_name}: canonical taunt duration unresolved",
            )
            return RotationTankTauntMaintenanceAssessment(
                requirement=requirement,
                duration_seconds=None,
                matching_casts=(),
                active_intervals=(),
                uncovered_windows=((requirement.active_start_seconds, requirement.active_end_seconds),),
                required_seconds=requirement.active_end_seconds - requirement.active_start_seconds,
                covered_seconds=0.0,
                resolved=False,
                satisfied=False,
                evidence=tuple(getattr(duration_resolution, "evidence", ())),
                unresolved=tuple(
                    f"{requirement.requirement_id}: {message}" for message in messages
                ),
            )

        duration = float(getattr(duration_resolution, "duration_seconds"))
        matching: list[RotationAction] = []
        intervals: list[RotationTankTauntMaintenanceInterval] = []
        requested_name = requirement.source_skill_name.casefold()
        requested_target = requirement.target_key.casefold()

        for action in plan.actions:
            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                continue
            if str(action.name or "").strip().casefold() != requested_name:
                continue
            action_target = str(getattr(action, "target_key", None) or "").strip()
            if not action_target or action_target.casefold() != requested_target:
                continue
            if requirement.bar is not None and action.bar != requirement.bar:
                continue

            raw_start = float(action.time_seconds)
            raw_end = raw_start + duration
            if raw_end < requirement.active_start_seconds:
                continue
            if raw_start > requirement.active_end_seconds:
                continue

            matching.append(action)
            intervals.append(
                RotationTankTauntMaintenanceInterval(
                    cast_time_seconds=raw_start,
                    active_start_seconds=max(raw_start, requirement.active_start_seconds),
                    active_end_seconds=min(raw_end, requirement.active_end_seconds),
                    bar=action.bar,
                    target_key=requirement.target_key,
                )
            )

        merged = self._merge_intervals(
            tuple(
                (item.active_start_seconds, item.active_end_seconds)
                for item in intervals
                if item.active_end_seconds >= item.active_start_seconds
            )
        )
        uncovered = self._uncovered_windows(
            start=requirement.active_start_seconds,
            end=requirement.active_end_seconds,
            covered=merged,
        )
        covered_seconds = sum(max(0.0, end - start) for start, end in merged)
        required_seconds = requirement.active_end_seconds - requirement.active_start_seconds

        return RotationTankTauntMaintenanceAssessment(
            requirement=requirement,
            duration_seconds=duration,
            matching_casts=tuple(matching),
            active_intervals=tuple(intervals),
            uncovered_windows=uncovered,
            required_seconds=required_seconds,
            covered_seconds=min(required_seconds, covered_seconds),
            resolved=True,
            satisfied=not uncovered,
            evidence=tuple(getattr(duration_resolution, "evidence", ())),
        )

    def evaluate_candidate(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        requirements: tuple[RotationTankTauntMaintenanceRequirement, ...],
    ) -> RotationCandidateRoleHardObligationEvidence:
        if not requirements:
            return RotationCandidateRoleHardObligationEvidence(
                candidate_id=candidate.candidate_id,
                satisfied=None,
                reasons=(
                    "tank taunt maintenance hard obligation unavailable: no explicit target-specific maintenance requirement supplied",
                ),
            )

        seen_ids: set[str] = set()
        assessments: list[RotationTankTauntMaintenanceAssessment] = []
        for requirement in requirements:
            if requirement.requirement_id in seen_ids:
                raise ValueError(
                    f"duplicate tank taunt maintenance requirement id: {requirement.requirement_id}"
                )
            seen_ids.add(requirement.requirement_id)
            assessments.append(self.assess(plan=candidate.plan, requirement=requirement))

        reasons: list[str] = []
        unresolved = [item for item in assessments if not item.resolved]
        if unresolved:
            for item in unresolved:
                reasons.extend(item.unresolved)
            return RotationCandidateRoleHardObligationEvidence(
                candidate_id=candidate.candidate_id,
                satisfied=None,
                reasons=tuple(dict.fromkeys(reasons)),
            )

        failed = [item for item in assessments if not item.satisfied]
        if failed:
            for item in failed:
                gaps = ", ".join(
                    f"{start:g}-{end:g}s" for start, end in item.uncovered_windows
                ) or "unknown gap"
                reasons.append(
                    f"{item.requirement.requirement_id}: target {item.requirement.target_key} "
                    f"taunt maintenance has uncovered window(s) {gaps}"
                )
            return RotationCandidateRoleHardObligationEvidence(
                candidate_id=candidate.candidate_id,
                satisfied=False,
                reasons=tuple(reasons),
            )

        return RotationCandidateRoleHardObligationEvidence(
            candidate_id=candidate.candidate_id,
            satisfied=True,
            reasons=tuple(
                f"{item.requirement.requirement_id}: target {item.requirement.target_key} "
                f"continuously taunted for {item.required_seconds:g}s"
                for item in assessments
            ),
        )

    @staticmethod
    def _merge_intervals(
        intervals: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], ...]:
        if not intervals:
            return ()
        ordered = sorted(intervals)
        merged: list[tuple[float, float]] = []
        start, end = ordered[0]
        for next_start, next_end in ordered[1:]:
            if next_start <= end + 1e-9:
                end = max(end, next_end)
                continue
            merged.append((start, end))
            start, end = next_start, next_end
        merged.append((start, end))
        return tuple(merged)

    @staticmethod
    def _uncovered_windows(
        *,
        start: float,
        end: float,
        covered: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], ...]:
        cursor = start
        gaps: list[tuple[float, float]] = []
        for covered_start, covered_end in covered:
            if covered_end < start or covered_start > end:
                continue
            clipped_start = max(start, covered_start)
            clipped_end = min(end, covered_end)
            if clipped_start > cursor + 1e-9:
                gaps.append((cursor, clipped_start))
            cursor = max(cursor, clipped_end)
            if cursor >= end - 1e-9:
                break
        if cursor < end - 1e-9:
            gaps.append((cursor, end))
        return tuple(gaps)


__all__ = [
    "RotationTankTauntMaintenanceAssessment",
    "RotationTankTauntMaintenanceInterval",
    "RotationTankTauntMaintenanceRequirement",
    "RotationTankTauntMaintenanceService",
]
