from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogService,
    ExtremeActualHealClassRouteEntry,
)
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealEvaluationCache,
)
from services.extreme_maximum_healing_event_class_route_catalog_service import (
    ExtremeMaximumHealingEventClassRouteCatalogResult,
    ExtremeMaximumHealingEventClassRouteCatalogService,
    ExtremeMaximumHealingEventRouteEntry,
)
from services.extreme_maximum_healing_event_finalist_selection_service import (
    ExtremeMaximumHealingEventFinalistSelectionResult,
    ExtremeMaximumHealingEventFinalistSelectionService,
)
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogService,
    ExtremeSorcererBloodMagicClassRouteEntry,
)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventFinalistOptimizationResult:
    entries: tuple[ExtremeMaximumHealingEventRouteEntry, ...]
    best_scored: ExtremeMaximumHealingEventRouteEntry | None
    best_complete: ExtremeMaximumHealingEventRouteEntry | None
    selection: ExtremeMaximumHealingEventFinalistSelectionResult
    errors: tuple[str, ...]
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def global_maximum_proven(self) -> bool:
        # Stage 2 intentionally optimizes only a screened shortlist. Even a fully
        # complete finalist therefore cannot prove that a pruned family/route
        # would not overtake after whole-build mutation.
        return False


class ExtremeMaximumHealingEventFinalistOptimizationService:
    """Fully optimize concrete Stage-1 finalists without rerunning route discovery."""

    SEARCH_SCOPE = (
        "STAGE 2: full whole-build optimization of selected Stage-1 finalists",
        "exact screened class route, active-bar slot, and heal/trigger preserved",
        "hypothetical route progression rebuilt before finalist optimization",
        "shared structural ordinary-heal evaluation cache across finalists",
    )

    def __init__(
        self,
        *,
        ordinary: ExtremeActualHealClassRouteCatalogService | None = None,
        blood_magic: ExtremeSorcererBloodMagicClassRouteCatalogService | None = None,
        selector: ExtremeMaximumHealingEventFinalistSelectionService | None = None,
        aggregator: ExtremeMaximumHealingEventClassRouteCatalogService | None = None,
    ) -> None:
        self.ordinary = ordinary or ExtremeActualHealClassRouteCatalogService()
        self.blood_magic = blood_magic or ExtremeSorcererBloodMagicClassRouteCatalogService()
        self.selector = selector or ExtremeMaximumHealingEventFinalistSelectionService()
        self.aggregator = aggregator or ExtremeMaximumHealingEventClassRouteCatalogService(
            ordinary=self.ordinary,
            blood_magic=self.blood_magic,
        )

    def optimize(
        self,
        baseline_build: PlayerBuild,
        screening: ExtremeMaximumHealingEventClassRouteCatalogResult,
        *,
        active_bar: str = "front",
        max_passes: int = 6,
        max_families: int = 8,
        routes_per_family: int = 3,
    ) -> ExtremeMaximumHealingEventFinalistOptimizationResult:
        selection = self.selector.select(
            screening,
            max_families=max_families,
            routes_per_family=routes_per_family,
        )
        ordinary_progression = self.ordinary._progression(baseline_build)
        blood_progression = self.blood_magic._progression(baseline_build)
        ordinary_evaluation_cache: ExtremeActualHealEvaluationCache = {}

        optimized: list[ExtremeMaximumHealingEventRouteEntry] = []
        errors: list[str] = []
        for finalist in selection.finalists:
            try:
                if finalist.source_kind == "ordinary_skill":
                    source = finalist.route_entry
                    route_progression = self.ordinary.progression_normalizer.normalize(
                        ordinary_progression,
                        source.route,
                    )
                    optimization = self.ordinary.optimizer.optimize(
                        source.candidate_build,
                        source.candidate.entity_id,
                        active_bar=active_bar,
                        max_passes=max(1, int(max_passes)),
                        progression_override=route_progression,
                        evaluation_cache=ordinary_evaluation_cache,
                    )
                    entry = ExtremeActualHealClassRouteEntry(
                        route=source.route,
                        candidate=source.candidate,
                        slotted_index=source.slotted_index,
                        candidate_build=source.candidate_build,
                        optimization=optimization,
                    )
                    optimized.append(self.aggregator._ordinary_entry(entry))
                    continue

                if finalist.source_kind == "blood_magic":
                    source = finalist.route_entry
                    route_progression = self.blood_magic.progression_normalizer.normalize(
                        blood_progression,
                        source.route,
                    )
                    optimization = self.blood_magic.blood_magic.optimize(
                        source.candidate_build,
                        active_bar=active_bar,
                        max_passes=max(1, int(max_passes)),
                        progression_override=route_progression,
                    )
                    entry = ExtremeSorcererBloodMagicClassRouteEntry(
                        route=source.route,
                        trigger=source.trigger,
                        slotted_index=source.slotted_index,
                        candidate_build=source.candidate_build,
                        optimization=optimization,
                    )
                    optimized.append(self.aggregator._blood_magic_entry(entry))
                    continue

                errors.append(
                    f"Unsupported Stage-2 finalist source: {finalist.source_kind}: {finalist.source_name}"
                )
            except (ValueError, LookupError) as exc:
                errors.append(
                    f"{finalist.source_name} on {','.join(finalist.route.equipped_skill_lines)}: {exc}"
                )

        ranked = tuple(sorted(optimized, key=self.aggregator._rank_key))
        scored = tuple(entry for entry in ranked if entry.event_value is not None)
        complete = tuple(entry for entry in scored if entry.mechanic_complete)
        omitted = tuple(
            dict.fromkeys(
                (
                    *selection.omitted_scope,
                    *screening.omitted_scope,
                )
            )
        )
        return ExtremeMaximumHealingEventFinalistOptimizationResult(
            entries=ranked,
            best_scored=scored[0] if scored else None,
            best_complete=complete[0] if complete else None,
            selection=selection,
            errors=tuple(errors),
            search_scope=self.SEARCH_SCOPE,
            omitted_scope=omitted,
        )
