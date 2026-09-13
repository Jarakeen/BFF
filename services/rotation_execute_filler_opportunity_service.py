from __future__ import annotations

"""Discover runtime-active execute opportunities without mutating the plan.

This service is intentionally conservative. It only considers replacing one
ordinary same-bar no-duration skill with another same-bar no-duration skill that
has positive canonical execute evidence and is ACTIVE for the supplied runtime
target Health snapshot.

It does not decide whether the execute is a damage upgrade. Damage comparison and
actual plan mutation belong to later layers. Due-refresh and duration-bearing
skills are deliberately outside this opportunity lane.
"""

from collections.abc import Callable
from dataclasses import dataclass

from minmax.combat_state_snapshot import CombatStateSnapshot
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteCandidateEvidenceService,
)
from services.rotation_execute_runtime_state_service import (
    RotationExecuteRuntimeStateService,
    RotationExecuteRuntimeStatus,
)


RotationExecuteSnapshotResolver = Callable[[float], CombatStateSnapshot | None]


@dataclass(frozen=True)
class RotationExecuteFillerOpportunity:
    time_seconds: float
    bar: str
    current_skill_name: str
    execute_skill_name: str
    current_priority: int
    execute_priority: int
    target_identity: str
    active_thresholds: tuple[float, ...]


@dataclass(frozen=True)
class RotationExecuteFillerOpportunityResult:
    opportunities: tuple[RotationExecuteFillerOpportunity, ...]
    unresolved: tuple[str, ...] = ()


class RotationExecuteFillerOpportunityService:
    """Find legal execute-vs-filler comparison points from explicit runtime evidence."""

    def __init__(
        self,
        *,
        evidence_service: RotationExecuteCandidateEvidenceService | None = None,
        runtime_state_service: RotationExecuteRuntimeStateService | None = None,
    ) -> None:
        self.evidence_service = evidence_service or RotationExecuteCandidateEvidenceService()
        self.runtime_state_service = runtime_state_service or RotationExecuteRuntimeStateService()

    def find(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList,
        duration_rules: tuple[RotationRecastRule, ...] = (),
        snapshot_resolver: RotationExecuteSnapshotResolver,
        target_identity: str,
    ) -> RotationExecuteFillerOpportunityResult:
        target = str(target_identity or "").strip()
        if not target:
            return RotationExecuteFillerOpportunityResult(
                opportunities=(),
                unresolved=("execute opportunity target identity is required",),
            )

        duration_names = {rule.skill_name.casefold() for rule in duration_rules}
        resolved_priorities = priorities.resolve()
        priority_by_key = {
            (row.entry.bar, row.entry.skill_name.casefold()): row.effective_priority
            for row in resolved_priorities
        }

        execute_by_bar: dict[str, list[tuple[str, int, RotationExecuteCandidateEvidence]]] = {
            "front": [],
            "back": [],
        }
        unresolved: list[str] = []
        for row in resolved_priorities:
            entry = row.entry
            if entry.slot == 6:
                continue
            if entry.skill_name.casefold() in duration_names:
                continue
            evidence = self.evidence_service.resolve(entry.skill_name)
            if evidence.components:
                execute_by_bar[entry.bar].append(
                    (entry.skill_name, row.effective_priority, evidence)
                )
            elif evidence.unresolved:
                unresolved.extend(evidence.unresolved)

        opportunities: list[RotationExecuteFillerOpportunity] = []
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            if action.bar not in execute_by_bar:
                continue
            current_key = action.name.casefold()
            if current_key in duration_names:
                continue
            current_priority = priority_by_key.get((str(action.bar), current_key))
            if current_priority is None:
                unresolved.append(
                    f"explicit priority is unavailable for scheduled filler {action.name!r} on {action.bar} bar"
                )
                continue

            snapshot = snapshot_resolver(float(action.time_seconds))
            if snapshot is None:
                unresolved.append(
                    f"execute runtime snapshot is unavailable at {action.time_seconds:g}s"
                )
                continue

            for execute_name, execute_priority, evidence in execute_by_bar[action.bar]:
                if execute_name.casefold() == current_key:
                    continue
                runtime = self.runtime_state_service.resolve(
                    candidate=evidence,
                    snapshot=snapshot,
                    target_identity=target,
                )
                if runtime.status is RotationExecuteRuntimeStatus.UNKNOWN:
                    unresolved.extend(runtime.unresolved)
                    continue
                if runtime.status is not RotationExecuteRuntimeStatus.ACTIVE:
                    continue
                thresholds = tuple(
                    sorted({float(component.threshold) for component in runtime.active_components})
                )
                opportunities.append(
                    RotationExecuteFillerOpportunity(
                        time_seconds=float(action.time_seconds),
                        bar=str(action.bar),
                        current_skill_name=action.name,
                        execute_skill_name=execute_name,
                        current_priority=int(current_priority),
                        execute_priority=int(execute_priority),
                        target_identity=target,
                        active_thresholds=thresholds,
                    )
                )

        opportunities.sort(
            key=lambda row: (
                row.time_seconds,
                row.bar,
                row.execute_priority,
                row.execute_skill_name.casefold(),
                row.current_skill_name.casefold(),
            )
        )
        return RotationExecuteFillerOpportunityResult(
            opportunities=tuple(opportunities),
            unresolved=tuple(self._dedupe(unresolved)),
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result


__all__ = [
    "RotationExecuteFillerOpportunity",
    "RotationExecuteFillerOpportunityResult",
    "RotationExecuteFillerOpportunityService",
    "RotationExecuteSnapshotResolver",
]
