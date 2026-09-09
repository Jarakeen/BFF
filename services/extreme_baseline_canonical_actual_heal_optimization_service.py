from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationResult,
)
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


class ExtremeBaselineCanonicalActualHealOptimizationService(
    ExtremeCanonicalActualHealOptimizationService
):
    """Score one canonical heal on the supplied build without build mutations.

    This is a screening primitive for the route catalog. It preserves the exact
    hypothetical progression snapshot, active bar, canonical recipient/event
    grouping, Healing Done, CP, class passives, and crit rules, but deliberately
    performs zero race/gear/Mundus/attribute/bar candidate passes.
    """

    SCREENING_SCOPE = (
        "baseline-only canonical Actual Heal route screening",
        "zero whole-build mutation passes",
    )
    SCREENING_OMITTED = (
        "whole-build mutation optimization intentionally omitted during route screening",
    )

    def optimize(
        self,
        baseline_build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
        max_passes: int = 0,
        progression_override=None,
    ) -> ExtremeActualHealOptimizationResult:
        _ = max_passes
        normalized_entity = str(entity_id or "").strip()
        if not normalized_entity:
            raise ValueError("Healing entity_id is required")

        resolution = MinmaxCharacterProgressionAdapter(
            self.optimizer.build_service.canonical.catalog_service
        ).resolve(baseline_build)
        if not resolution.resolved:
            raise ValueError("; ".join(resolution.unresolved))

        progression = progression_override or resolution.progression
        build_id = (
            str(getattr(baseline_build, "BuildId", "") or "").strip()
            or str(baseline_build.BuildName or "").strip()
            or "saved-build"
        )
        current = PlayerBuild.from_dict(baseline_build.to_dict())
        event, unresolved = self._evaluate(
            current,
            progression=progression,
            character_id=resolution.character_id,
            build_id=f"{build_id}:extreme-actual-heal:screen",
            entity_id=normalized_entity,
            active_bar=active_bar,
        )
        self._score(event)
        return ExtremeActualHealOptimizationResult(
            entity_id=normalized_entity,
            baseline_build=PlayerBuild.from_dict(baseline_build.to_dict()),
            optimized_build=current,
            baseline_event=event,
            optimized_event=event,
            steps=(),
            unresolved=tuple(unresolved),
            search_scope=self.SCREENING_SCOPE,
            omitted_scope=self.SCREENING_OMITTED,
        )
