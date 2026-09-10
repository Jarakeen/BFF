from __future__ import annotations

"""Canonical from-scratch structural scoring for core Extreme stat records.

This layer bridges the exhaustive structural universe to the existing canonical
character-sheet evaluator.  It does not add ESO formulas.  Race, legal class
route, all 64-point attribute allocations, and active-bar context are materialized
onto an ordinary ``PlayerBuild`` and evaluated through ``ExtremeOptimizationService``.

The resulting record remains a lower bound while dynamic axes such as gear,
skills, CP, consumables, and runtime state are still deferred.  Structural
exhaustiveness is useful evidence, but it is not permission to print a fake world
record.
"""

from pathlib import Path
from typing import Any

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_core_stat_record_service import ExtremeCoreStatRecordService
from services.extreme_global_search_universe_service import (
    ExtremeGlobalSearchUniverseService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)
from services.extreme_structural_global_search_service import (
    ExtremeStructuralCandidate,
    ExtremeStructuralGlobalSearchResult,
    ExtremeStructuralGlobalSearchService,
)


_RATIO_KEYS = frozenset({"weapon_critical", "spell_critical", "critical_damage", "healing_done"})
_RATING_KEYS = frozenset({"health_recovery", "magicka_recovery", "stamina_recovery"})


class ExtremeCanonicalStructuralStatEvaluator:
    """Evaluate one structural candidate through the canonical sheet pipeline."""

    def __init__(
        self,
        *,
        optimizer: ExtremeOptimizationService,
        progression_service: ExtremeHypotheticalClassProgressionService,
    ) -> None:
        self.optimizer = optimizer
        self.progression_service = progression_service

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        objective = self.optimizer.objective(objective_key)

        base = PlayerBuild(
            Name="Extreme Structural Candidate",
            BuildName=f"Extreme Structural {objective.label}",
            Race=candidate.race,
            EsoClass=candidate.class_route.base_class.value,
            Role="Experimental",
        )
        build = ExtremeHealClassRouteService.materialize_build(base, candidate.class_route)
        build.Race = candidate.race
        build.AttributeHealth = int(candidate.attributes.health)
        build.AttributeMagicka = int(candidate.attributes.magicka)
        build.AttributeStamina = int(candidate.attributes.stamina)

        progression = CharacterProgression(
            attributes=candidate.attributes,
            passive_ranks={},
            passive_cp_points={},
        )
        progression = self.progression_service.normalize(progression, candidate.class_route)

        identity = candidate.identity
        candidate_id = "|".join(
            (
                str(identity[0]),
                str(identity[1]),
                ",".join(identity[2]),
                f"h{identity[3]}m{identity[4]}s{identity[5]}",
                str(identity[6]),
            )
        )
        value, unresolved = self.optimizer._evaluate(
            build,
            progression=progression,
            character_id="extreme-structural-global",
            build_id=f"extreme-structural-global:{candidate_id}",
            objective=objective,
            active_bar=candidate.active_bar,
        )
        payload = {
            "build": build.to_dict(),
            "race": candidate.race,
            "base_class": candidate.class_route.base_class.value,
            "class_skill_lines": tuple(candidate.class_route.equipped_skill_lines),
            "attributes": {
                "health": int(candidate.attributes.health),
                "magicka": int(candidate.attributes.magicka),
                "stamina": int(candidate.attributes.stamina),
            },
            "active_bar": candidate.active_bar,
        }
        return float(value), payload, tuple(unresolved)


class ExtremeStructuralCoreStatRecordService:
    """Return exhaustive structural lower bounds for executable core stat records."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeOptimizationService | None = None,
        search_service: ExtremeStructuralGlobalSearchService[dict[str, Any]] | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeOptimizationService(database_path=database_path)
        if search_service is not None:
            self.search_service = search_service
            return

        resolved_database = Path(database_path or self.optimizer.database_path)
        universe = ExtremeGlobalSearchUniverseService(resolved_database)
        evaluator = ExtremeCanonicalStructuralStatEvaluator(
            optimizer=self.optimizer,
            progression_service=ExtremeHypotheticalClassProgressionService(resolved_database),
        )
        self.search_service = ExtremeStructuralGlobalSearchService(
            universe,
            scorer=evaluator,
        )

    @staticmethod
    def _unit(objective_key: str) -> str:
        if objective_key in _RATIO_KEYS:
            return "ratio"
        if objective_key in _RATING_KEYS:
            return "rating"
        return "points"

    def record(self, objective_key: str) -> ExtremeRecordResult:
        key = str(objective_key or "").strip().casefold()
        if not ExtremeCoreStatRecordService.supports(key):
            raise ValueError(
                f"Extreme structural core-stat search does not support objective: {objective_key!r}"
            )

        result: ExtremeStructuralGlobalSearchResult[dict[str, Any]] = self.search_service.search(key)
        coverage = ExtremeRecordSearchCoverage(
            searched=tuple(result.structural_scope),
            omitted=tuple(result.deferred_dynamic_axes),
            candidates_screened=int(result.candidates_scored),
            candidates_optimized=int(result.candidates_scored),
            denominator_proven=bool(result.global_denominator_proven),
        )

        if result.best is None:
            return ExtremeRecordResult.for_objective(
                key,
                raw_value=None,
                proof_status=ExtremeRecordProofStatus.UNRESOLVED,
                unresolved=tuple(
                    dict.fromkeys(
                        (
                            "Structural Extreme search produced no scored candidate",
                            *result.unresolved,
                        )
                    )
                ),
                search_coverage=coverage,
            )

        winner = result.best
        explanation = (
            "Exhaustively searched race × legal class/subclass route × all 64-point attribute allocations × active-bar context.",
            f"Scored {result.candidates_scored:,} structural candidates; {result.ties_at_best:,} tied at the best structural value.",
            "Dynamic axes remain deferred, so this is a structural lower bound rather than a globally proven Extreme Record.",
        )
        return ExtremeRecordResult.for_objective(
            key,
            raw_value=float(winner.value),
            proof_status=(
                ExtremeRecordProofStatus.PROVEN
                if result.global_denominator_proven and not result.unresolved
                else ExtremeRecordProofStatus.LOWER_BOUND
            ),
            winning_build=winner.payload,
            unit=self._unit(key),
            unresolved=tuple(result.unresolved),
            search_coverage=coverage,
            explanation=explanation,
        )
