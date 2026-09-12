from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from minmax.skill_coefficient_repository import ability_entity_id
from minmax.skill_component_runtime_binding import (
    RuntimeScheduleBindingResult,
    SkillComponentRuntimeState,
    schedule_skill_component_runtime_events,
)
from minmax.skill_component_trigger_relationship import SkillComponentTriggerType
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationCandidatePeriodicDamageTimingEvidenceService,
    RotationPeriodicDamageTimingEntry,
)


class PeriodicDamageRefreshBoundary(str, Enum):
    """Reviewed behavior for an old periodic instance at an exact recast boundary."""

    REPLACE_BEFORE_RECAST_TICK = "replace_before_recast_tick"
    ALLOW_OLD_TICK_AT_RECAST = "allow_old_tick_at_recast"


class PeriodicDamageMagnitudePolicy(str, Enum):
    """Reviewed rule for which combat state owns periodic tick magnitude."""

    SNAPSHOT_AT_CAST = "snapshot_at_cast"
    DYNAMIC_AT_TICK = "dynamic_at_tick"


@dataclass(frozen=True)
class RotationPeriodicDamageRuntimeSemantics:
    """Reviewed runtime facts that canonical cadence/duration evidence cannot infer.

    These values are evidence inputs, not defaults. A caller must identify the
    canonical skill/component, preserve a source, and state the first-tick offset
    and refresh-boundary behavior explicitly before concrete tick timestamps are
    legal. Magnitude timing is intentionally separate from tick scheduling: callers
    must also review whether one cast snapshots its damage state or each tick reads
    the live state at that tick instant before DD output may claim complete damage.
    """

    skill_entity_id: str
    coefficient_number: int
    first_tick_offset_seconds: float
    refresh_boundary: PeriodicDamageRefreshBoundary
    source: str
    verified_interval_seconds: float | None = None
    magnitude_policy: PeriodicDamageMagnitudePolicy | None = None

    def __post_init__(self) -> None:
        entity_id = ability_entity_id(self.skill_entity_id)
        if not entity_id:
            raise ValueError("periodic damage runtime semantics require a skill identity")
        object.__setattr__(self, "skill_entity_id", entity_id)
        if self.coefficient_number <= 0:
            raise ValueError("periodic damage coefficient_number must be positive")
        offset = float(self.first_tick_offset_seconds)
        if not math.isfinite(offset) or offset < 0:
            raise ValueError("first_tick_offset_seconds must be finite and non-negative")
        object.__setattr__(self, "first_tick_offset_seconds", offset)
        if not isinstance(self.refresh_boundary, PeriodicDamageRefreshBoundary):
            object.__setattr__(
                self,
                "refresh_boundary",
                PeriodicDamageRefreshBoundary(str(self.refresh_boundary)),
            )
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("periodic damage runtime semantics require provenance")
        object.__setattr__(self, "source", source)
        if self.verified_interval_seconds is not None:
            interval = float(self.verified_interval_seconds)
            if not math.isfinite(interval) or interval <= 0:
                raise ValueError("verified_interval_seconds must be finite and positive")
            object.__setattr__(self, "verified_interval_seconds", interval)
        if self.magnitude_policy is not None and not isinstance(
            self.magnitude_policy,
            PeriodicDamageMagnitudePolicy,
        ):
            object.__setattr__(
                self,
                "magnitude_policy",
                PeriodicDamageMagnitudePolicy(str(self.magnitude_policy)),
            )


@dataclass(frozen=True)
class RotationPeriodicDamageRuntimeProjectionEntry:
    action: RotationAction
    coefficient_number: int
    events: tuple[RuntimeEvent, ...]
    active_end_time_seconds: float | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationPeriodicDamageRuntimeProjection:
    entries: tuple[RotationPeriodicDamageRuntimeProjectionEntry, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved and all(not entry.unresolved for entry in self.entries)


class RotationCandidatePeriodicDamageRuntimeProjectionService:
    """Bind reviewed periodic semantics to the shared runtime scheduler.

    Cadence and duration remain owned by the periodic timing evidence service.
    Concrete recurring scheduling remains owned by the shared Phase 7 runtime
    binder. This layer only binds reviewed first-tick/refresh facts to one
    rotation plan and clips occurrences to the next recast and plan horizon.
    Magnitude timing is preserved on the semantics record for the DD output layer;
    it does not alter event scheduling here.
    """

    _EPSILON = 1e-9

    def __init__(
        self,
        timing_service: RotationCandidatePeriodicDamageTimingEvidenceService,
    ) -> None:
        self.timing_service = timing_service

    def project(
        self,
        *,
        plan: RotationPlan,
        semantics: tuple[RotationPeriodicDamageRuntimeSemantics, ...],
    ) -> RotationPeriodicDamageRuntimeProjection:
        semantic_map = {
            (item.skill_entity_id, item.coefficient_number): item for item in semantics
        }
        entries: list[RotationPeriodicDamageRuntimeProjectionEntry] = []
        unresolved: list[str] = []

        for action_index, action in enumerate(plan.actions):
            if action.kind is not RotationActionKind.SKILL:
                continue
            timing_report = self.timing_service.inspect_action(action)
            unresolved.extend(timing_report.unresolved)

            for timing_entry in timing_report.entries:
                projected = self._project_entry(
                    plan=plan,
                    action_index=action_index,
                    action=action,
                    timing_entry=timing_entry,
                    semantics=semantic_map.get(
                        (ability_entity_id(timing_entry.source_name), timing_entry.coefficient_number)
                    ),
                )
                entries.append(projected)
                unresolved.extend(projected.unresolved)

        return RotationPeriodicDamageRuntimeProjection(
            entries=tuple(entries),
            unresolved=tuple(dict.fromkeys(value for value in unresolved if value)),
        )

    def _project_entry(
        self,
        *,
        plan: RotationPlan,
        action_index: int,
        action: RotationAction,
        timing_entry: RotationPeriodicDamageTimingEntry,
        semantics: RotationPeriodicDamageRuntimeSemantics | None,
    ) -> RotationPeriodicDamageRuntimeProjectionEntry:
        if timing_entry.unresolved or timing_entry.timing is None or timing_entry.duration_seconds is None:
            messages = timing_entry.unresolved or (
                f"{timing_entry.source_name} coefficient {timing_entry.coefficient_number}: periodic timing is incomplete",
            )
            return self._unresolved_entry(action, timing_entry, *messages)

        if semantics is None:
            return self._unresolved_entry(
                action,
                timing_entry,
                f"{timing_entry.source_name} coefficient {timing_entry.coefficient_number}: reviewed first-tick/refresh semantics are unavailable",
            )

        natural_end = action.time_seconds + float(timing_entry.duration_seconds)
        next_recast = self._next_recast_time(plan, action_index, action)
        active_end = min(natural_end, plan.duration_seconds)
        if next_recast is not None:
            active_end = min(active_end, next_recast)

        first_occurrence = action.time_seconds + semantics.first_tick_offset_seconds
        evidence = (
            *timing_entry.evidence,
            f"first tick offset {semantics.first_tick_offset_seconds:g}s from {semantics.source}",
            f"refresh boundary {semantics.refresh_boundary.value} from {semantics.source}",
        )
        if semantics.magnitude_policy is not None:
            evidence = (
                *evidence,
                f"magnitude policy {semantics.magnitude_policy.value} from {semantics.source}",
            )

        if first_occurrence > active_end + self._EPSILON:
            return RotationPeriodicDamageRuntimeProjectionEntry(
                action=action,
                coefficient_number=timing_entry.coefficient_number,
                events=(),
                active_end_time_seconds=active_end,
                evidence=tuple(dict.fromkeys(evidence)),
            )

        state = SkillComponentRuntimeState(
            first_occurrence_time_seconds=first_occurrence,
            active_end_time_seconds=active_end,
            verified_interval_seconds=semantics.verified_interval_seconds,
        )
        scheduled = schedule_skill_component_runtime_events(
            timing_entry.timing,
            state,
            trigger=SkillComponentTriggerType.DAMAGE_DEALT.value,
            source=f"{timing_entry.source_name} coefficient {timing_entry.coefficient_number}",
        )
        if isinstance(scheduled, RuntimeScheduleBindingResult):
            messages = tuple(
                f"{timing_entry.source_name} coefficient {timing_entry.coefficient_number}: runtime binding requires {name}"
                for name in scheduled.unresolved
            )
            return self._unresolved_entry(action, timing_entry, *messages)

        filtered: list[RuntimeEvent] = []
        for event in scheduled:
            if event.time_seconds > plan.duration_seconds + self._EPSILON:
                continue
            if event.time_seconds > natural_end + self._EPSILON:
                continue
            if next_recast is not None:
                if semantics.refresh_boundary is PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK:
                    if event.time_seconds >= next_recast - self._EPSILON:
                        continue
                elif event.time_seconds > next_recast + self._EPSILON:
                    continue
            filtered.append(event)

        return RotationPeriodicDamageRuntimeProjectionEntry(
            action=action,
            coefficient_number=timing_entry.coefficient_number,
            events=tuple(filtered),
            active_end_time_seconds=active_end,
            evidence=tuple(dict.fromkeys(evidence)),
        )

    @staticmethod
    def _next_recast_time(
        plan: RotationPlan,
        action_index: int,
        action: RotationAction,
    ) -> float | None:
        identity = ability_entity_id(action.name or "")
        for later in plan.actions[action_index + 1 :]:
            if later.kind is not RotationActionKind.SKILL:
                continue
            if ability_entity_id(later.name or "") == identity:
                return later.time_seconds
        return None

    @staticmethod
    def _unresolved_entry(
        action: RotationAction,
        timing_entry: RotationPeriodicDamageTimingEntry,
        *messages: str,
    ) -> RotationPeriodicDamageRuntimeProjectionEntry:
        return RotationPeriodicDamageRuntimeProjectionEntry(
            action=action,
            coefficient_number=timing_entry.coefficient_number,
            events=(),
            active_end_time_seconds=None,
            unresolved=tuple(dict.fromkeys(str(message).strip() for message in messages if str(message).strip())),
        )


__all__ = [
    "PeriodicDamageMagnitudePolicy",
    "PeriodicDamageRefreshBoundary",
    "RotationCandidatePeriodicDamageRuntimeProjectionService",
    "RotationPeriodicDamageRuntimeProjection",
    "RotationPeriodicDamageRuntimeProjectionEntry",
    "RotationPeriodicDamageRuntimeSemantics",
]
