from __future__ import annotations

"""Classify canonical gear-set bonus breakpoints by Extreme objective relevance.

This layer is intentionally conservative.  It consumes the shared
``ExtremeGearSetObjectiveService`` instead of reparsing bonus descriptions or
inventing objective math.  A breakpoint may be pruned only when the canonical
resolver completes and proves that the active set bonuses contribute no positive
amount to the requested maximize objective.

Unmapped, conditional, or otherwise unresolved active bonuses remain explicit
proof blockers.  Cross-set dominance is deliberately not inferred here: slot
cost, slot eligibility, and the ability to equip multiple distinct sets make a
simple larger-delta comparison unsafe.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
    ExtremeGearSetObjectiveService,
)


class ExtremeGearSetObjectiveRelevance(str, Enum):
    RELEVANT = "relevant"
    PROVEN_IRRELEVANT = "proven_irrelevant"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ExtremeGearSetObjectiveBreakpointEvidence:
    set_id: int
    set_name: str
    piece_count: int
    objective_key: str
    status: ExtremeGearSetObjectiveRelevance
    reviewed_delta: float
    candidate: ExtremeGearSetObjectiveCandidate

    @property
    def safe_to_prune(self) -> bool:
        return self.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT


@dataclass(frozen=True)
class ExtremeGearSetObjectiveRelevanceCatalog:
    objective_key: str
    evidence: tuple[ExtremeGearSetObjectiveBreakpointEvidence, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def relevant(self) -> tuple[ExtremeGearSetObjectiveBreakpointEvidence, ...]:
        return tuple(
            row for row in self.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.RELEVANT
        )

    @property
    def proven_irrelevant(self) -> tuple[ExtremeGearSetObjectiveBreakpointEvidence, ...]:
        return tuple(
            row for row in self.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
        )

    @property
    def unresolved_evidence(self) -> tuple[ExtremeGearSetObjectiveBreakpointEvidence, ...]:
        return tuple(
            row for row in self.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
        )

    @property
    def denominator_proven(self) -> bool:
        return bool(self.evidence) and not self.unresolved and not self.unresolved_evidence

    @property
    def candidate_set_ids(self) -> tuple[int, ...]:
        """Distinct sets that must remain in an objective search denominator."""

        values = {
            row.set_id
            for row in self.evidence
            if row.status is not ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
        }
        return tuple(sorted(values))


class ExtremeGearSetObjectiveRelevanceService:
    """Build proof-safe objective relevance evidence at every set-bonus breakpoint."""

    def __init__(
        self,
        repository: GearSetRepository,
        *,
        resolver: GearSetEffectResolver | None = None,
    ) -> None:
        self.repository = repository
        self.resolver = resolver or GearSetEffectResolver()

    def build(
        self,
        objective_key: str,
        breakpoint_catalog: ExtremeGearSetBonusBreakpointCatalog,
    ) -> ExtremeGearSetObjectiveRelevanceCatalog:
        key = str(objective_key or "").strip().casefold()
        # Fail closed immediately for objectives the canonical projection layer
        # has not reviewed.
        ExtremeGearSetObjectiveService._target_stats(key)

        evidence: list[ExtremeGearSetObjectiveBreakpointEvidence] = []
        unresolved: list[str] = list(breakpoint_catalog.unresolved)

        for breakpoint_set in breakpoint_catalog.mechanically_relevant_sets:
            gear_set = self.repository.get_set_by_id(breakpoint_set.set_id)
            if gear_set is None:
                unresolved.append(
                    f"Gear set {breakpoint_set.name} ({breakpoint_set.set_id}) missing from canonical repository"
                )
                continue

            for piece_count in breakpoint_set.bonus_counts:
                candidate = ExtremeGearSetObjectiveService.candidate_for_set(
                    self.repository,
                    gear_set.name,
                    key,
                    equipped_piece_count=piece_count,
                    resolver=self.resolver,
                )
                if candidate.unresolved:
                    status = ExtremeGearSetObjectiveRelevance.UNRESOLVED
                    unresolved.extend(candidate.unresolved)
                elif candidate.reviewed_delta > 1e-12:
                    status = ExtremeGearSetObjectiveRelevance.RELEVANT
                else:
                    status = ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT

                evidence.append(
                    ExtremeGearSetObjectiveBreakpointEvidence(
                        set_id=int(candidate.set_id),
                        set_name=candidate.set_name,
                        piece_count=int(piece_count),
                        objective_key=key,
                        status=status,
                        reviewed_delta=float(candidate.reviewed_delta),
                        candidate=candidate,
                    )
                )

        evidence.sort(
            key=lambda row: (
                row.set_name.casefold(),
                row.set_name,
                row.set_id,
                row.piece_count,
            )
        )
        return ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key=key,
            evidence=tuple(evidence),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
