from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from services.class_mastery_classification_service import ClassMasteryBoundary
from services.extreme_class_configuration_service import ExtremeClassConfigurationService
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService
from services.extreme_subclass_skill_bar_service import (
    ExtremeSubclassSkillBarResult,
    ExtremeSubclassSkillBarService,
    ExtremeSubclassTwoBarResult,
)
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationResult,
    ExtremeSubclassSlotAllocationService,
)
from services.named_buff_resolution_service import NamedBuffContribution


class ExtremeClassRouteKind(str, Enum):
    PURE_MASTERY = "pure_mastery"
    SUBCLASS = "subclass"


@dataclass(frozen=True)
class ExtremeClassRouteCandidate:
    route_kind: ExtremeClassRouteKind
    base_class: CharacterClass
    objective_key: str
    equipped_skill_lines: tuple[str, ...]
    mastery_names: tuple[str, ...] = ()
    projected_delta: float | None = None
    boundary: ClassMasteryBoundary | None = None
    score_status: str = ""
    reviewed_line_ids: tuple[str, ...] = ()
    slot_counts: tuple[tuple[str, int], ...] = ()
    reviewed_sources: tuple[str, ...] = ()
    buff_context_notes: tuple[str, ...] = ()
    active_bar: str = "front"
    skill_bar_names: tuple[str, ...] = ()
    skill_bar_ability_ids: tuple[int, ...] = ()
    front_skill_bar_names: tuple[str, ...] = ()
    front_skill_bar_ability_ids: tuple[int, ...] = ()
    back_skill_bar_names: tuple[str, ...] = ()
    back_skill_bar_ability_ids: tuple[int, ...] = ()

    @property
    def is_scored(self) -> bool:
        return self.projected_delta is not None


@dataclass(frozen=True)
class ExtremeClassRouteComparison:
    objective_key: str
    routes: tuple[ExtremeClassRouteCandidate, ...]
    best_reviewed_pure_route: ExtremeClassRouteCandidate | None
    unresolved_subclass_count: int
    best_reviewed_subclass_lower_bound: ExtremeClassRouteCandidate | None = None
    reviewed_subclass_lower_bound_count: int = 0

    @property
    def can_declare_global_winner(self) -> bool:
        return self.unresolved_subclass_count == 0


@dataclass(frozen=True)
class _ReviewedSubclassBuild:
    allocation: ExtremeSubclassSlotAllocationResult
    bars: ExtremeSubclassTwoBarResult
    projected_delta: float
    reviewed_sources: tuple[str, ...]
    buff_context_notes: tuple[str, ...]


class ExtremeClassRouteComparisonService:
    """Compare reviewed pure-class mastery routes against legal subclass routes.

    Subclass lower bounds require a reviewed six-slot allocation plus concrete
    canonical front and back bars. Slot-count passives and reviewed standing
    skill effects are optimized together rather than choosing a passive-only bar
    first and merely decorating it afterward.

    Standing skills retain explicit scope: active-bar effects only apply on the
    selected bar, either-bar effects apply if present on either bar, and runtime
    effects remain excluded until combat state can prove uptime. External named
    buffs may shape skill choice and stacking, but route scores only receive the
    marginal value added beyond that shared external context. Suppressed duplicate
    buff evidence is carried on each scored route for downstream explanation.

    Legal allocations whose reviewed passive contribution is proven zero remain
    eligible for bar materialization. This prevents skill-only standing effects
    from disappearing merely because the passive layer had nothing numeric to
    contribute for the requested objective.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        skill_bar_service: ExtremeSubclassSkillBarService | None = None,
    ) -> None:
        self.mastery_pairs = ExtremeClassMasteryPairService(database_path)
        self.skill_bars = skill_bar_service or ExtremeSubclassSkillBarService(database_path)

    def _materialize_two_bars(
        self,
        slot_counts: tuple[tuple[str, int], ...],
        *,
        objective_key: str,
        reference_value: float | None,
        external_effects: tuple[NamedBuffContribution, ...],
    ) -> ExtremeSubclassTwoBarResult | None:
        materialize_two_bars = getattr(self.skill_bars, "materialize_two_bars", None)
        if callable(materialize_two_bars):
            try:
                return materialize_two_bars(
                    slot_counts,
                    slot_counts,
                    objective_key=objective_key,
                    reference_value=reference_value,
                    external_effects=external_effects,
                )
            except TypeError:
                try:
                    return materialize_two_bars(
                        slot_counts,
                        slot_counts,
                        objective_key=objective_key,
                        reference_value=reference_value,
                    )
                except TypeError:
                    return materialize_two_bars(
                        slot_counts,
                        slot_counts,
                        objective_key=objective_key,
                    )

        def materialize_one():
            try:
                return self.skill_bars.materialize(
                    slot_counts,
                    objective_key=objective_key,
                    reference_value=reference_value,
                    external_effects=external_effects,
                )
            except TypeError:
                try:
                    return self.skill_bars.materialize(
                        slot_counts,
                        objective_key=objective_key,
                        reference_value=reference_value,
                    )
                except TypeError:
                    return self.skill_bars.materialize(
                        slot_counts,
                        objective_key=objective_key,
                    )

        front = materialize_one()
        back = materialize_one()
        if front is None or back is None:
            return None
        return ExtremeSubclassTwoBarResult(front=front, back=back)

    @staticmethod
    def _active_bar(
        bars: ExtremeSubclassTwoBarResult,
        active_bar: str,
    ) -> ExtremeSubclassSkillBarResult:
        return bars.front if active_bar == "front" else bars.back

    def _best_reviewed_subclass_build(
        self,
        equipped_skill_lines: tuple[str, ...],
        objective_key: str,
        *,
        reference_value: float | None,
        active_bar: str,
        external_effects: tuple[NamedBuffContribution, ...],
    ) -> tuple[_ReviewedSubclassBuild | None, bool]:
        allocations = ExtremeSubclassSlotAllocationService.reviewed_allocations(
            equipped_skill_lines,
            objective_key,
            reference_value=reference_value,
            include_known_zero=True,
        )
        if not allocations:
            return None, False

        best: _ReviewedSubclassBuild | None = None
        materialized_any = False
        for allocation in allocations:
            bars = self._materialize_two_bars(
                allocation.slot_counts,
                objective_key=objective_key,
                reference_value=reference_value,
                external_effects=external_effects,
            )
            if bars is None:
                continue
            materialized_any = True
            skill_delta, skill_sources, buff_context_notes = (
                ExtremeSkillStandingEffectService.marginal_score_build_bars_explained(
                    bars.front.names,
                    bars.back.names,
                    objective_key,
                    active_bar=active_bar,
                    reference_value=reference_value,
                    external_effects=external_effects,
                )
            )
            candidate = _ReviewedSubclassBuild(
                allocation=allocation,
                bars=bars,
                projected_delta=allocation.projected_delta + skill_delta,
                reviewed_sources=allocation.reviewed_sources + skill_sources,
                buff_context_notes=buff_context_notes,
            )
            if best is None or (
                candidate.projected_delta > best.projected_delta + 1e-9
                or (
                    abs(candidate.projected_delta - best.projected_delta) <= 1e-9
                    and (
                        candidate.allocation.slot_counts,
                        candidate.bars.front.names,
                        candidate.bars.back.names,
                    )
                    < (
                        best.allocation.slot_counts,
                        best.bars.front.names,
                        best.bars.back.names,
                    )
                )
            ):
                best = candidate

        return best, materialized_any

    def compare(
        self,
        objective_key: str,
        *,
        reference_value: float | None = None,
        higher_max_resource: float | None = None,
        active_bar: str = "front",
        external_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> ExtremeClassRouteComparison:
        active_bar_key = str(active_bar or "").strip().casefold()
        if active_bar_key not in {"front", "back"}:
            raise ValueError("active_bar must be 'front' or 'back'")

        routes: list[ExtremeClassRouteCandidate] = []

        pure_rows = self.mastery_pairs.best_pure_class_routes(
            objective_key,
            reference_value=reference_value,
            higher_max_resource=higher_max_resource,
        )
        for row in pure_rows:
            pure_config = next(
                candidate
                for candidate in ExtremeClassConfigurationService.candidates_for_base_class(row.base_class)
                if candidate.is_pure_class
            )
            routes.append(
                ExtremeClassRouteCandidate(
                    route_kind=ExtremeClassRouteKind.PURE_MASTERY,
                    base_class=row.base_class,
                    objective_key=objective_key,
                    equipped_skill_lines=pure_config.equipped_skill_lines,
                    mastery_names=row.passive_names,
                    projected_delta=row.projected_delta,
                    boundary=row.boundary,
                    score_status="reviewed_mastery_delta",
                    active_bar=active_bar_key,
                )
            )

        subclass_count = 0
        reviewed_lower_bound_count = 0
        for config in ExtremeClassConfigurationService.all_candidates():
            if config.is_pure_class:
                continue
            subclass_count += 1

            reviewed_build, materialized_any = self._best_reviewed_subclass_build(
                config.equipped_skill_lines,
                objective_key,
                reference_value=reference_value,
                active_bar=active_bar_key,
                external_effects=external_effects,
            )
            if reviewed_build is not None:
                reviewed_lower_bound_count += 1
                allocation = reviewed_build.allocation
                bars = reviewed_build.bars
                active = self._active_bar(bars, active_bar_key)
                projected_delta: float | None = reviewed_build.projected_delta
                score_status = "reviewed_subclass_materialized_lower_bound"
                slot_counts = allocation.slot_counts
                reviewed_sources = reviewed_build.reviewed_sources
                buff_context_notes = reviewed_build.buff_context_notes
                reviewed_line_ids = tuple(
                    line for line, count in slot_counts if count > 0
                )
                skill_bar_names = active.names
                skill_bar_ability_ids = tuple(skill.ability_id for skill in active.skills)
                front_skill_bar_names = bars.front.names
                front_skill_bar_ability_ids = tuple(skill.ability_id for skill in bars.front.skills)
                back_skill_bar_names = bars.back.names
                back_skill_bar_ability_ids = tuple(skill.ability_id for skill in bars.back.skills)
            else:
                projected_delta = None
                score_status = (
                    "pending_canonical_bar_materialization"
                    if materialized_any is False
                    and ExtremeSubclassSlotAllocationService.reviewed_allocations(
                        config.equipped_skill_lines,
                        objective_key,
                        reference_value=reference_value,
                        include_known_zero=True,
                    )
                    else "pending_subclass_effect_resolution"
                )
                slot_counts = ()
                reviewed_sources = ()
                buff_context_notes = ()
                reviewed_line_ids = ()
                skill_bar_names = ()
                skill_bar_ability_ids = ()
                front_skill_bar_names = ()
                front_skill_bar_ability_ids = ()
                back_skill_bar_names = ()
                back_skill_bar_ability_ids = ()

            routes.append(
                ExtremeClassRouteCandidate(
                    route_kind=ExtremeClassRouteKind.SUBCLASS,
                    base_class=config.base_class,
                    objective_key=objective_key,
                    equipped_skill_lines=config.equipped_skill_lines,
                    mastery_names=(),
                    projected_delta=projected_delta,
                    boundary=None,
                    score_status=score_status,
                    reviewed_line_ids=reviewed_line_ids,
                    slot_counts=slot_counts,
                    reviewed_sources=reviewed_sources,
                    buff_context_notes=buff_context_notes,
                    active_bar=active_bar_key,
                    skill_bar_names=skill_bar_names,
                    skill_bar_ability_ids=skill_bar_ability_ids,
                    front_skill_bar_names=front_skill_bar_names,
                    front_skill_bar_ability_ids=front_skill_bar_ability_ids,
                    back_skill_bar_names=back_skill_bar_names,
                    back_skill_bar_ability_ids=back_skill_bar_ability_ids,
                )
            )

        best_pure = next(
            (
                row
                for row in sorted(
                    (item for item in routes if item.route_kind is ExtremeClassRouteKind.PURE_MASTERY),
                    key=lambda item: (-(item.projected_delta or 0.0), item.base_class.value),
                )
            ),
            None,
        )
        best_subclass = next(
            (
                row
                for row in sorted(
                    (
                        item
                        for item in routes
                        if item.route_kind is ExtremeClassRouteKind.SUBCLASS
                        and item.projected_delta is not None
                    ),
                    key=lambda item: (
                        -(item.projected_delta or 0.0),
                        item.base_class.value,
                        item.equipped_skill_lines,
                        item.slot_counts,
                        item.skill_bar_names,
                        item.front_skill_bar_names,
                        item.back_skill_bar_names,
                    ),
                )
            ),
            None,
        )

        return ExtremeClassRouteComparison(
            objective_key=objective_key,
            routes=tuple(routes),
            best_reviewed_pure_route=best_pure,
            unresolved_subclass_count=subclass_count,
            best_reviewed_subclass_lower_bound=best_subclass,
            reviewed_subclass_lower_bound_count=reviewed_lower_bound_count,
        )
