from __future__ import annotations

"""Proof-owned attribute reduction for standing Extreme MOST Actual Heal.

The objective-neutral Extreme universe contains every legal 64-point
Health/Magicka/Stamina split.  Standing H1 currently scores coefficient-backed
heals through the canonical type-8 relation, whose resource input is the larger
of Max Magicka and Max Stamina.  For a fixed non-attribute build state, each of
those resources is monotonic in only its own attribute-point count, so every
mixed allocation is dominated by at least one pure 64-point resource endpoint.

This service owns that reduction only for the currently reviewed standing H1
coefficient path.  It refuses the proof when the selected heal contains an active
coefficient type other than type 8.  Conditional/emergency scenarios remain
separate callers and do not inherit this proof merely because the same skill can
appear there.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_coefficients import is_inactive_skill_coefficient
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService


@dataclass(frozen=True)
class ExtremeActualHealAttributeProjectionResult:
    candidates: tuple[BuildCandidate, ...]
    source_allocations_reviewed: int
    denominator_proven: bool
    search_scope: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealAttributeProjectionService:
    """Reduce the complete H1 attribute simplex to its two resource endpoints."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
    ) -> None:
        if coefficient_repository is None:
            if database_path is None:
                raise ValueError(
                    "database_path is required when coefficient_repository is not supplied"
                )
            coefficient_repository = SkillCoefficientRepository(database_path)
        self.coefficients = coefficient_repository

    @staticmethod
    def _allocation(build: PlayerBuild) -> tuple[int, int, int]:
        return (
            int(build.AttributeHealth or 0),
            int(build.AttributeMagicka or 0),
            int(build.AttributeStamina or 0),
        )

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        entity_id: str,
        character_id: str,
        baseline_build_id: str,
    ) -> ExtremeActualHealAttributeProjectionResult:
        normalized_entity = str(entity_id or "").strip()
        source_allocations = ExtremeGlobalSearchUniverseService.attribute_allocations()
        unresolved: list[str] = []

        resolution = self.coefficients.resolve_entity_id(normalized_entity)
        if resolution.rank is None:
            unresolved.extend(tuple(resolution.unresolved))
            if not resolution.unresolved:
                unresolved.append(
                    f"H1 attribute projection could not resolve healing entity: {normalized_entity!r}"
                )
            return ExtremeActualHealAttributeProjectionResult(
                candidates=(),
                source_allocations_reviewed=len(source_allocations),
                denominator_proven=False,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        active_coefficients = tuple(
            coefficient
            for coefficient in resolution.rank.coefficients
            if not is_inactive_skill_coefficient(coefficient)
        )
        if not active_coefficients:
            unresolved.append(
                f"{normalized_entity}: no active coefficients available for H1 attribute proof"
            )
        unsupported = tuple(
            coefficient
            for coefficient in active_coefficients
            if str(coefficient.type or "").strip() != "8"
        )
        if unsupported:
            unresolved.append(
                f"{normalized_entity}: H1 attribute projection supports only type-8 active coefficients; "
                "found "
                + ", ".join(
                    f"#{coefficient.coefficient_number}=type {coefficient.type}"
                    for coefficient in unsupported
                )
            )

        expected_source_count = (
            (ExtremeGlobalSearchUniverseService.ATTRIBUTE_POINTS + 1)
            * (ExtremeGlobalSearchUniverseService.ATTRIBUTE_POINTS + 2)
            // 2
        )
        if len(source_allocations) != expected_source_count:
            unresolved.append(
                "Canonical H1 attribute source does not contain the complete 64-point simplex: "
                f"expected {expected_source_count}, found {len(source_allocations)}"
            )

        if unresolved:
            return ExtremeActualHealAttributeProjectionResult(
                candidates=(),
                source_allocations_reviewed=len(source_allocations),
                denominator_proven=False,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        before = self._allocation(baseline_build)
        total = int(ExtremeGlobalSearchUniverseService.ATTRIBUTE_POINTS)
        endpoints = (
            ("magicka", (0, total, 0)),
            ("stamina", (0, 0, total)),
        )
        result: list[BuildCandidate] = []
        for resource, allocation in endpoints:
            if before == allocation:
                continue
            build = PlayerBuild.from_dict(baseline_build.to_dict())
            (
                build.AttributeHealth,
                build.AttributeMagicka,
                build.AttributeStamina,
            ) = allocation
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-attributes:type8-endpoint:{resource}",
                    path="Attributes",
                    before={
                        "health": before[0],
                        "magicka": before[1],
                        "stamina": before[2],
                    },
                    after={
                        "health": allocation[0],
                        "magicka": allocation[1],
                        "stamina": allocation[2],
                    },
                    source="extreme:actual-heal:attribute-projection",
                )
            )

        scope = (
            f"all {len(source_allocations):,} legal 64-point attribute allocations proof-reduced "
            "to pure Magicka/Stamina endpoints for the reviewed standing type-8 H1 coefficient path",
        )
        return ExtremeActualHealAttributeProjectionResult(
            candidates=tuple(result),
            source_allocations_reviewed=len(source_allocations),
            denominator_proven=True,
            search_scope=scope,
        )


__all__ = [
    "ExtremeActualHealAttributeProjectionResult",
    "ExtremeActualHealAttributeProjectionService",
]
