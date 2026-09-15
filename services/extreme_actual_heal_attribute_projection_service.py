from __future__ import annotations

"""Proof-owned attribute reduction for standing Extreme MOST Actual Heal.

The objective-neutral Extreme universe contains every legal 64-point
Health/Magicka/Stamina split. Standing H1 currently scores reviewed HEAL
components through the canonical type-8 relation, whose resource input is the
larger of Max Magicka and Max Stamina. For a fixed non-attribute build state,
each resource is monotonic in only its own attribute-point count.

A mixed allocation may therefore be discarded only when every HEAL component
that can contribute to the selected event is on the reviewed type-8 path and is
non-decreasing in highest resource. That second guard matters: type 8 describes
the formula shape, not the sign of its resource coefficient.

This service owns that reduction only for the currently reviewed standing H1
coefficient path. Conditional/emergency scenarios remain separate callers and do
not inherit this proof merely because the same skill can appear there.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_coefficients import is_inactive_skill_coefficient
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
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
        component_repository: SkillComponentRepository | None = None,
    ) -> None:
        if coefficient_repository is None or component_repository is None:
            if database_path is None:
                raise ValueError(
                    "database_path is required when coefficient/component repositories are not supplied"
                )
        self.coefficients = coefficient_repository or SkillCoefficientRepository(database_path)
        self.components = component_repository or SkillComponentRepository(database_path)

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

        heal_numbers = {
            int(component.coefficient_number)
            for component in self.components.get_for_skill_rank(
                resolution.rank.skill_rank_id
            )
            if component.effect_kind is SkillEffectKind.HEAL
        }
        if not heal_numbers:
            unresolved.append(
                f"{normalized_entity}: no HEAL-classified coefficients available for H1 attribute proof"
            )

        heal_coefficients = tuple(
            coefficient
            for coefficient in resolution.rank.coefficients
            if (
                not is_inactive_skill_coefficient(coefficient)
                and int(coefficient.coefficient_number) in heal_numbers
            )
        )
        found_numbers = {int(coefficient.coefficient_number) for coefficient in heal_coefficients}
        missing_numbers = tuple(sorted(heal_numbers - found_numbers))
        if missing_numbers:
            unresolved.append(
                f"{normalized_entity}: HEAL coefficient definitions missing for H1 attribute proof: "
                + ", ".join(str(number) for number in missing_numbers)
            )

        unsupported = tuple(
            coefficient
            for coefficient in heal_coefficients
            if str(coefficient.type or "").strip() != "8"
        )
        if unsupported:
            unresolved.append(
                f"{normalized_entity}: H1 attribute projection supports only type-8 HEAL coefficients; "
                "found "
                + ", ".join(
                    f"#{coefficient.coefficient_number}=type {coefficient.type}"
                    for coefficient in unsupported
                )
            )

        negative_resource_slopes = tuple(
            coefficient
            for coefficient in heal_coefficients
            if float(coefficient.a) < 0.0
        )
        if negative_resource_slopes:
            unresolved.append(
                f"{normalized_entity}: H1 attribute endpoint dominance is not proven for negative "
                "HEAL resource coefficient(s): "
                + ", ".join(
                    f"#{coefficient.coefficient_number} A={coefficient.a:g}"
                    for coefficient in negative_resource_slopes
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
            "to pure Magicka/Stamina endpoints for standing H1 HEAL components with reviewed "
            "type-8 non-negative highest-resource scaling",
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
