from __future__ import annotations

"""Audit runtime/proc coverage for Extreme max-resource objectives.

This service owns no ESO stat arithmetic.  It composes the already-proven named-
gear relevance denominator with the reviewed contextual-passive ledger and exposes
which target-stat effects still require an executable runtime/condition witness.

A global max-resource record may close the runtime axis only when:

* the named-gear relevance denominator is proven;
* every reviewed contextual resource passive is canonically applied; and
* every objective-relevant conditional gear effect has an execution owner.

Until that last condition is true, the exact set/condition evidence remains an
explicit blocker rather than being treated as zero or silently assumed active.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveReviewService,
    ExtremeResourceContextualPassiveStatus,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class ExtremeResourceRuntimeConditionEvidence:
    set_id: int
    set_name: str
    piece_count: int
    condition: str
    stat: str
    value: float
    source: str

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.set_id,
            self.set_name,
            self.piece_count,
            self.condition,
            self.stat,
            self.value,
            self.source,
        )


@dataclass(frozen=True)
class ExtremeResourceRuntimeCoverageAudit:
    objective_key: str
    contextual_passives_reviewed: tuple[str, ...]
    conditional_gear_effects: tuple[ExtremeResourceRuntimeConditionEvidence, ...]
    condition_markers: tuple[str, ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        # Conditional gear effects are denominator evidence, not execution proof.
        # They remain open until a later runtime-state service owns each marker.
        return bool(
            self.denominator_proven
            and not self.conditional_gear_effects
            and not self.unresolved
        )


class ExtremeResourceRuntimeCoverageAuditService:
    """Expose the remaining runtime/proc blockers for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES
    _DATABASE_CACHE: dict[
        tuple[str, str],
        ExtremeResourceRuntimeCoverageAudit,
    ] = {}

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: GearSetRepository | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no gear-set repository is supplied")
        self.repository = repository or GearSetRepository(database_path)  # type: ignore[arg-type]
        # Shared caching is intentionally limited to the canonical repository type.
        # Injected/fake repositories used by focused tests keep instance-local behavior.
        self._database_path = (
            str(getattr(self.repository, "database_path", "") or "").strip()
            if type(self.repository) is GearSetRepository
            else ""
        )
        self._instance_cache: dict[str, ExtremeResourceRuntimeCoverageAudit] = {}

    def build(self, objective_key: str) -> ExtremeResourceRuntimeCoverageAudit:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource runtime objective: {objective_key!r}")

        cached = self._instance_cache.get(key)
        if cached is not None:
            return cached

        shared_key = (self._database_path, key)
        if self._database_path:
            cached = self._DATABASE_CACHE.get(shared_key)
            if cached is not None:
                self._instance_cache[key] = cached
                return cached

        breakpoints = ExtremeGearSetBonusBreakpointService(self.repository).build()
        relevance = ExtremeGearSetObjectiveRelevanceService(self.repository).build(
            key,
            breakpoints,
        )
        unresolved: list[str] = list(relevance.unresolved)

        passive_rows = ExtremeResourceContextualPassiveReviewService.build(key)
        for row in passive_rows:
            if row.status is not ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED:
                unresolved.append(
                    f"Contextual resource passive still needs execution: "
                    f"{row.skill_line} / {row.passive_name} ({row.status.value})"
                )

        target_stats = ExtremeGearSetObjectiveService._target_stats(key)
        conditional: dict[tuple[object, ...], ExtremeResourceRuntimeConditionEvidence] = {}
        for row in relevance.evidence:
            if row.status is not ExtremeGearSetObjectiveRelevance.RELEVANT:
                continue
            for effect in row.candidate.source_effects:
                if effect.stat not in target_stats or not effect.condition:
                    continue
                evidence = ExtremeResourceRuntimeConditionEvidence(
                    set_id=int(row.set_id),
                    set_name=row.set_name,
                    piece_count=int(row.piece_count),
                    condition=str(effect.condition).strip(),
                    stat=effect.stat.value,
                    value=float(effect.value),
                    source=str(effect.source or "").strip(),
                )
                conditional.setdefault(evidence.identity, evidence)

        ordered = tuple(
            sorted(
                conditional.values(),
                key=lambda item: (
                    item.condition.casefold(),
                    item.set_name.casefold(),
                    item.set_id,
                    item.piece_count,
                    item.stat,
                    item.value,
                ),
            )
        )
        markers = tuple(sorted({row.condition for row in ordered}, key=str.casefold))
        denominator_proven = bool(
            relevance.denominator_proven
            and passive_rows
            and not unresolved
        )

        result = ExtremeResourceRuntimeCoverageAudit(
            objective_key=key,
            contextual_passives_reviewed=tuple(
                f"{row.skill_line}: {row.passive_name}" for row in passive_rows
            ),
            conditional_gear_effects=ordered,
            condition_markers=markers,
            denominator_proven=denominator_proven,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
        self._instance_cache[key] = result
        if self._database_path:
            self._DATABASE_CACHE[shared_key] = result
        return result


__all__ = [
    "ExtremeResourceRuntimeConditionEvidence",
    "ExtremeResourceRuntimeCoverageAudit",
    "ExtremeResourceRuntimeCoverageAuditService",
]
