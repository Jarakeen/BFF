from __future__ import annotations

"""Replay priority-aware duration scheduling to recover queue-instance provenance.

Production plans intentionally keep the compact historical unresolved diagnostics.
This diagnostic service instead observes the existing priority-aware scheduler's
selection seam and records the original seed action instance carried by each queued
skill. It does not change scheduling policy or production plan output.
"""

from dataclasses import dataclass

from minmax.priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationPlan
from minmax.rotation_recast import RotationRecastRule


@dataclass(frozen=True)
class RotationDisplacementQueueInstance:
    skill_name: str
    bar: str
    source_time_seconds: float
    source_sequence: int


@dataclass(frozen=True)
class RotationDisplacementQueueDecision:
    slot_time_seconds: float
    bar: str
    incoming: RotationDisplacementQueueInstance
    selected: RotationDisplacementQueueInstance
    remaining_queue: tuple[RotationDisplacementQueueInstance, ...]


@dataclass(frozen=True)
class RotationDisplacementSpilloverProvenance:
    skill_name: str
    bar: str
    source_time_seconds: float | None
    source_sequence: int | None
    last_observed_queue_time_seconds: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.source_time_seconds is not None and not self.unresolved


@dataclass(frozen=True)
class RotationPriorityDisplacementProvenanceReplay:
    plan: RotationPlan
    decisions: tuple[RotationDisplacementQueueDecision, ...]
    spillovers: tuple[RotationDisplacementSpilloverProvenance, ...]


class _TracingPriorityAwareDurationRotationScheduler(
    PriorityAwareDurationRotationScheduler
):
    def __init__(self, priorities: AbilityPriorityList) -> None:
        super().__init__(priorities)
        self.decisions: list[RotationDisplacementQueueDecision] = []

    def _select_displaced_candidate(
        self,
        *,
        queue: list[RotationAction],
        incoming: RotationAction,
        bar: str | None,
    ) -> RotationAction:
        selected = super()._select_displaced_candidate(
            queue=queue,
            incoming=incoming,
            bar=bar,
        )
        normalized_bar = str(bar or "").strip().casefold()
        if normalized_bar not in {"front", "back"}:
            return selected
        self.decisions.append(
            RotationDisplacementQueueDecision(
                slot_time_seconds=float(incoming.time_seconds),
                bar=normalized_bar,
                incoming=self._instance(incoming, normalized_bar),
                selected=self._instance(selected, normalized_bar),
                remaining_queue=tuple(
                    self._instance(action, normalized_bar) for action in queue if action.name
                ),
            )
        )
        return selected

    @staticmethod
    def _instance(action: RotationAction, bar: str) -> RotationDisplacementQueueInstance:
        return RotationDisplacementQueueInstance(
            skill_name=str(action.name or ""),
            bar=bar,
            source_time_seconds=float(action.time_seconds),
            source_sequence=int(action.sequence),
        )


class RotationPriorityDisplacementProvenanceReplayService:
    """Replay the canonical priority scheduler and map horizon tails to seed instances."""

    _HORIZON_MARKER = " was displaced beyond the "

    def replay(
        self,
        *,
        seed_plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        priorities: AbilityPriorityList,
    ) -> RotationPriorityDisplacementProvenanceReplay:
        scheduler = _TracingPriorityAwareDurationRotationScheduler(priorities)
        refined = scheduler.refine(seed_plan, tuple(rules))
        spillovers = tuple(
            self._resolve_spillover(
                text=str(raw or ""),
                decisions=tuple(scheduler.decisions),
            )
            for raw in refined.unresolved
            if self._HORIZON_MARKER in str(raw or "")
        )
        return RotationPriorityDisplacementProvenanceReplay(
            plan=refined,
            decisions=tuple(scheduler.decisions),
            spillovers=spillovers,
        )

    @classmethod
    def _resolve_spillover(
        cls,
        *,
        text: str,
        decisions: tuple[RotationDisplacementQueueDecision, ...],
    ) -> RotationDisplacementSpilloverProvenance:
        skill_name, bar = cls._parse_horizon(text)
        matches: list[tuple[float, RotationDisplacementQueueInstance]] = []
        for decision in decisions:
            if decision.bar != bar:
                continue
            for instance in decision.remaining_queue:
                if instance.skill_name.casefold() == skill_name.casefold():
                    matches.append((decision.slot_time_seconds, instance))
        if not matches:
            return RotationDisplacementSpilloverProvenance(
                skill_name=skill_name,
                bar=bar,
                source_time_seconds=None,
                source_sequence=None,
                last_observed_queue_time_seconds=None,
                unresolved=(
                    "spillover instance was not observed in the queue-selection trace; "
                    "it may have entered during the final refresh claim or lacks replay provenance",
                ),
            )

        latest_time = max(item[0] for item in matches)
        latest_instances = {
            (item.source_time_seconds, item.source_sequence): item
            for time_seconds, item in matches
            if time_seconds == latest_time
        }
        if len(latest_instances) != 1:
            return RotationDisplacementSpilloverProvenance(
                skill_name=skill_name,
                bar=bar,
                source_time_seconds=None,
                source_sequence=None,
                last_observed_queue_time_seconds=latest_time,
                unresolved=(
                    "multiple same-skill action instances remain plausible at the last observed queue point",
                ),
            )
        instance = next(iter(latest_instances.values()))
        return RotationDisplacementSpilloverProvenance(
            skill_name=skill_name,
            bar=bar,
            source_time_seconds=instance.source_time_seconds,
            source_sequence=instance.source_sequence,
            last_observed_queue_time_seconds=latest_time,
        )

    @staticmethod
    def _parse_horizon(text: str) -> tuple[str, str]:
        prefix = "skill '"
        if not text.startswith(prefix):
            raise ValueError(f"unsupported horizon displacement diagnostic: {text!r}")
        remainder = text[len(prefix) :]
        skill_name, separator, tail = remainder.partition("' was displaced beyond the ")
        if not separator:
            raise ValueError(f"unsupported horizon displacement diagnostic: {text!r}")
        if tail.endswith(" on front bar"):
            bar = "front"
        elif tail.endswith(" on back bar"):
            bar = "back"
        else:
            raise ValueError(f"unsupported horizon displacement bar: {text!r}")
        return skill_name, bar


__all__ = [
    "RotationDisplacementQueueDecision",
    "RotationDisplacementQueueInstance",
    "RotationDisplacementSpilloverProvenance",
    "RotationPriorityDisplacementProvenanceReplay",
    "RotationPriorityDisplacementProvenanceReplayService",
]
