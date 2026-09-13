from __future__ import annotations

"""Proof-reduce max-resource gear witnesses before canonical scoring.

The full named-gear and dual-bar denominator remains authoritative.  This service
runs *after* those legality proofs and collapses only active-snapshot realizations
that are canonically indistinguishable for the requested max-resource objective.

Ordinary mechanic-complete set identities may be forgotten when the objective
relevance ledger proves the same requested-stat effects.  Any unresolved,
conditional, search-state, or otherwise non-ordinary breakpoint keeps exact set
identity.  Active weapon shape/type semantics remain explicit.

The representative for each semantic class is the lexicographically smallest
physical identity, preserving the existing deterministic tie-break among members
that are proven to score identically.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)


@dataclass(frozen=True)
class ExtremeMaxResourceGearScoringFrontierResult:
    objective_key: str
    raw_realizations: tuple[ExtremeNamedGearSetRealization, ...]
    representatives: tuple[ExtremeNamedGearSetRealization, ...]
    semantic_classes: int
    duplicate_witnesses_pruned: int
    largest_equivalence_class: int
    reduction_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def reduction_percent(self) -> float:
        if not self.raw_realizations:
            return 0.0
        return 100.0 * self.duplicate_witnesses_pruned / len(self.raw_realizations)


class ExtremeMaxResourceGearScoringFrontierService:
    """Collapse only proven objective-scoring-equivalent active gear witnesses."""

    SUPPORTED_OBJECTIVES = frozenset({"max_health", "max_magicka", "max_stamina"})

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._relevance_cache: dict[str, ExtremeGearSetObjectiveRelevanceCatalog] = {}

    @staticmethod
    def physical_identity(realization: ExtremeNamedGearSetRealization) -> tuple[Any, ...]:
        return (
            tuple(int(value) for value in realization.set_ids),
            tuple(int(value) for value in realization.counts),
            realization.weapon_shape.value,
            tuple(
                (str(row.slot), int(row.set_id), str(row.weapon_type or ""))
                for row in realization.assignments
            ),
        )

    @classmethod
    def _member_signature(
        cls,
        evidence,
        objective_key: str,
        *,
        set_id: int,
        piece_count: int,
    ) -> tuple[Any, ...]:
        # Missing or unresolved evidence must never merge identities.
        if evidence is None:
            return ("identity_required", int(set_id), int(piece_count), "missing_evidence")

        if (
            evidence.status is not ExtremeGearSetObjectiveRelevance.RELEVANT
            or evidence.search_state_rule is not None
            or evidence.candidate.unresolved
        ):
            return (
                "identity_required",
                int(set_id),
                int(piece_count),
                evidence.status.value,
                repr(evidence.search_state_rule),
                tuple(evidence.candidate.unresolved),
            )

        target_stats = ExtremeGearSetObjectiveService._target_stats(objective_key)
        effects = tuple(
            sorted(
                ExtremeObjectiveNamedGearSetCatalogRealizationService._effect_signature(effect)
                for effect in evidence.candidate.source_effects
                if effect.stat in target_stats
            )
        )
        if not effects:
            return ("identity_required", int(set_id), int(piece_count), "no_target_effect")

        return (
            "ordinary_objective_semantics",
            int(piece_count),
            effects,
            float(evidence.reviewed_delta),
        )

    @classmethod
    def semantic_signature(
        cls,
        realization: ExtremeNamedGearSetRealization,
        evidence_by_key: dict[tuple[int, int], Any],
        objective_key: str,
    ) -> tuple[Any, ...]:
        member_by_set_id: dict[int, tuple[Any, ...]] = {}
        members: list[tuple[Any, ...]] = []
        for set_id, count in zip(realization.set_ids, realization.counts):
            evidence = evidence_by_key.get((int(set_id), int(count)))
            member = cls._member_signature(
                evidence,
                objective_key,
                set_id=int(set_id),
                piece_count=int(count),
            )
            member_by_set_id[int(set_id)] = member
            members.append(member)

        weapon_semantics = tuple(
            sorted(
                (
                    str(row.slot),
                    str(row.weapon_type or ""),
                    member_by_set_id.get(
                        int(row.set_id),
                        ("identity_required", int(row.set_id), "unknown_weapon_set"),
                    ),
                )
                for row in realization.assignments
                if str(row.slot) in {"Main Hand", "Off Hand"}
            )
        )
        return (
            tuple(sorted(members, key=repr)),
            realization.weapon_shape.value,
            weapon_semantics,
        )

    @classmethod
    def reduce_with_relevance(
        cls,
        objective_key: str,
        realizations: tuple[ExtremeNamedGearSetRealization, ...],
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    ) -> ExtremeMaxResourceGearScoringFrontierResult:
        key = str(objective_key or "").strip().casefold()
        if key not in cls.SUPPORTED_OBJECTIVES:
            return ExtremeMaxResourceGearScoringFrontierResult(
                objective_key=key,
                raw_realizations=tuple(realizations),
                representatives=tuple(realizations),
                semantic_classes=len(realizations),
                duplicate_witnesses_pruned=0,
                largest_equivalence_class=1 if realizations else 0,
                reduction_proven=False,
                unresolved=(f"Unsupported max-resource scoring frontier objective: {objective_key!r}",),
            )

        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in relevance.evidence
        }
        groups: dict[tuple[Any, ...], list[ExtremeNamedGearSetRealization]] = {}
        for realization in realizations:
            signature = cls.semantic_signature(realization, evidence_by_key, key)
            groups.setdefault(signature, []).append(realization)

        representatives = tuple(
            sorted(
                (
                    min(rows, key=cls.physical_identity)
                    for rows in groups.values()
                ),
                key=cls.physical_identity,
            )
        )
        largest = max((len(rows) for rows in groups.values()), default=0)
        return ExtremeMaxResourceGearScoringFrontierResult(
            objective_key=key,
            raw_realizations=tuple(realizations),
            representatives=representatives,
            semantic_classes=len(groups),
            duplicate_witnesses_pruned=max(0, len(realizations) - len(representatives)),
            largest_equivalence_class=largest,
            reduction_proven=True,
            # Relevance unresolved evidence is not collapsed because unresolved members
            # retain exact identity. Preserve it for proof/reporting without disabling the
            # safe reductions among mechanic-complete ordinary members.
            unresolved=tuple(relevance.unresolved),
        )

    def _relevance(self, objective_key: str) -> ExtremeGearSetObjectiveRelevanceCatalog:
        key = str(objective_key or "").strip().casefold()
        cached = self._relevance_cache.get(key)
        if cached is not None:
            return cached
        repository = GearSetRepository(self.database_path)
        breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
        relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(key, breakpoints)
        self._relevance_cache[key] = relevance
        return relevance

    def build(
        self,
        objective_key: str,
        realizations: tuple[ExtremeNamedGearSetRealization, ...],
    ) -> ExtremeMaxResourceGearScoringFrontierResult:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            return self.reduce_with_relevance(
                key,
                tuple(realizations),
                ExtremeGearSetObjectiveRelevanceCatalog(key, ()),
            )
        return self.reduce_with_relevance(key, tuple(realizations), self._relevance(key))
