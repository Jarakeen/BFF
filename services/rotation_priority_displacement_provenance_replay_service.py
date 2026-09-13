from __future__ import annotations

"""Replay priority-aware duration scheduling to recover queue-instance provenance.

Production plans intentionally keep the compact historical unresolved diagnostics.
This diagnostic service instead observes the existing priority-aware scheduler's
selection seam and records the original seed action instance carried by each queued
skill. It does not change scheduling policy or production plan output.

The scheduler's selection seam exposes the queue immediately after choosing one
candidate for a decision slot. If a due refresh then claims that same slot, production
puts the selected candidate back at the front of the queue. Replay reconstructs that
post-slot state from the existing refresh-claim diagnostic, allowing exact final queue
provenance without copying or modifying the production ``refine`` implementation.
"""

from dataclasses import dataclass
import re

from minmax.priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationPlan
from minmax.rotation_recast import RotationRecastRule


_REFRESH_CLAIM_PATTERN = re.compile(
    r"^refresh obligation for '(.+)' claimed the ([0-9]+(?:\.[0-9]+)?)s "
    r"(front|back)-bar slot from '(.+)'; displaced skill will cascade to the next same-bar skill slot$",
    re.IGNORECASE,
)


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
    plausible_instances: tuple[RotationDisplacementQueueInstance, ...] = ()
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
        decisions = tuple(scheduler.decisions)
        final_queue_by_bar = self._final_queue_by_bar(
            decisions=decisions,
            unresolved=tuple(refined.unresolved),
        )
        spillovers = tuple(
            self._resolve_spillover(
                text=str(raw or ""),
                final_queue_by_bar=final_queue_by_bar,
                decisions=decisions,
            )
            for raw in refined.unresolved
            if self._HORIZON_MARKER in str(raw or "")
        )
        return RotationPriorityDisplacementProvenanceReplay(
            plan=refined,
            decisions=decisions,
            spillovers=spillovers,
        )

    @classmethod
    def _final_queue_by_bar(
        cls,
        *,
        decisions: tuple[RotationDisplacementQueueDecision, ...],
        unresolved: tuple[str, ...],
    ) -> dict[str, tuple[RotationDisplacementQueueInstance, ...]]:
        refresh_claims = cls._refresh_claims(unresolved)
        result: dict[str, tuple[RotationDisplacementQueueInstance, ...]] = {}
        for bar in ("front", "back"):
            bar_decisions = tuple(item for item in decisions if item.bar == bar)
            if not bar_decisions:
                continue
            last = max(bar_decisions, key=lambda item: item.slot_time_seconds)
            queue = list(last.remaining_queue)
            claim = refresh_claims.get((last.slot_time_seconds, bar))
            if claim is not None:
                displaced_skill = claim[1]
                if displaced_skill.casefold() == last.selected.skill_name.casefold():
                    queue.insert(0, last.selected)
            result[bar] = tuple(queue)
        return result

    @staticmethod
    def _refresh_claims(
        unresolved: tuple[str, ...],
    ) -> dict[tuple[float, str], tuple[str, str]]:
        result: dict[tuple[float, str], tuple[str, str]] = {}
        for raw in unresolved:
            match = _REFRESH_CLAIM_PATTERN.match(str(raw or "").strip())
            if match is None:
                continue
            refresh_skill = match.group(1).strip()
            time_seconds = float(match.group(2))
            bar = match.group(3).casefold()
            displaced_skill = match.group(4).strip()
            result[(time_seconds, bar)] = (refresh_skill, displaced_skill)
        return result

    @classmethod
    def _resolve_spillover(
        cls,
        *,
        text: str,
        final_queue_by_bar: dict[str, tuple[RotationDisplacementQueueInstance, ...]],
        decisions: tuple[RotationDisplacementQueueDecision, ...],
    ) -> RotationDisplacementSpilloverProvenance:
        skill_name, bar = cls._parse_horizon(text)
        final_matches = tuple(
            instance
            for instance in final_queue_by_bar.get(bar, ())
            if instance.skill_name.casefold() == skill_name.casefold()
        )
        last_observed = max(
            (
                decision.slot_time_seconds
                for decision in decisions
                if decision.bar == bar
            ),
            default=None,
        )

        if len(final_matches) == 1:
            instance = final_matches[0]
            return RotationDisplacementSpilloverProvenance(
                skill_name=skill_name,
                bar=bar,
                source_time_seconds=instance.source_time_seconds,
                source_sequence=instance.source_sequence,
                last_observed_queue_time_seconds=last_observed,
                plausible_instances=final_matches,
            )

        if len(final_matches) > 1:
            return RotationDisplacementSpilloverProvenance(
                skill_name=skill_name,
                bar=bar,
                source_time_seconds=None,
                source_sequence=None,
                last_observed_queue_time_seconds=last_observed,
                plausible_instances=final_matches,
                unresolved=(
                    "multiple same-skill action instances survive in the reconstructed final queue; "
                    "the deduplicated production horizon diagnostic cannot identify one instance",
                ),
            )

        return RotationDisplacementSpilloverProvenance(
            skill_name=skill_name,
            bar=bar,
            source_time_seconds=None,
            source_sequence=None,
            last_observed_queue_time_seconds=last_observed,
            unresolved=(
                "spillover skill is absent from the reconstructed final queue; replay provenance is incomplete",
            ),
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
