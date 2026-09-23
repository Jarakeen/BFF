from __future__ import annotations

"""Run generated sustained-DPS search across the validated structural family denominator."""

from dataclasses import dataclass

from services.extreme_sustained_dps_generated_axis_inventory_service import (
    ExtremeSustainedDPSGeneratedAxisInventoryService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGlobalGeneratedSearchRoot:
    marker: str = "sustained-dps-global-root"


class ExtremeSustainedDPSGlobalGeneratedSearchService:
    """Prepend structural families to the existing generated-axis pipeline."""

    def __init__(
        self,
        *,
        structural_families: object,
        structural_materialization: object,
        pipeline: object,
        leaf_evaluation: object,
    ) -> None:
        self.structural_families = structural_families
        self.structural_materialization = structural_materialization
        self.pipeline = pipeline
        self.leaf_evaluation = leaf_evaluation

    def _structural_axis(
        self,
        *,
        dual_bar_frontier: object,
        candidate_id_prefix: str,
        duration_seconds: float,
        potion_cooldown_seconds: float | None,
        starting_ultimate: float,
        priorities: object,
        snapshot_resolver: object,
        target_identity: str,
        ultimate_generation_events: tuple[object, ...],
        heroism_windows: tuple[object, ...],
        use_scheduled_combat_attacks_for_ultimate: bool,
        duration_rules: tuple[object, ...],
        heavy_attack_windows: tuple[object, ...],
        heavy_attack_channel_blocks: tuple[object, ...],
        heavy_attack_channel_block_denominator_proven: bool,
        potion_cooldown_resolver: object | None,
        potion_cooldown_scenario: object | None,
    ) -> ExtremeSustainedDPSIndexedFrontierAxis:
        validated = self.structural_families.validate_denominator()
        if not validated.denominator_proven:
            detail = "; ".join(validated.unresolved)
            raise ValueError(
                "global generated sustained-DPS search requires a proven structural family denominator"
                + (f": {detail}" if detail else "")
            )

        def candidate_count(_state: object) -> int:
            return int(validated.choice_count)

        def candidate_at(_state: object, index: int):
            choice = self.structural_families.choice_at(index)
            materialized = self.structural_materialization.materialize(choice)
            if not materialized.complete:
                raise ValueError(
                    "structural family materialization is incomplete: "
                    + "; ".join(materialized.unresolved)
                )
            return self.pipeline.root(
                materialized.build,
                materialized.progression,
                dual_bar_frontier=dual_bar_frontier,
                candidate_id_prefix=(
                    f"{str(candidate_id_prefix or '').strip()}"
                    f"|structural-family:{choice.structural_family_index}"
                ),
                duration_seconds=float(duration_seconds),
                potion_cooldown_seconds=potion_cooldown_seconds,
                starting_ultimate=float(starting_ultimate),
                potion_cooldown_resolver=potion_cooldown_resolver,
                potion_cooldown_scenario=potion_cooldown_scenario,
                priorities=priorities,
                snapshot_resolver=snapshot_resolver,
                target_identity=target_identity,
                ultimate_generation_events=tuple(ultimate_generation_events),
                heroism_windows=tuple(heroism_windows),
                use_scheduled_combat_attacks_for_ultimate=bool(
                    use_scheduled_combat_attacks_for_ultimate
                ),
                duration_rules=tuple(duration_rules),
                heavy_attack_windows=tuple(heavy_attack_windows),
                heavy_attack_channel_blocks=tuple(heavy_attack_channel_blocks),
                heavy_attack_channel_block_denominator_proven=bool(
                    heavy_attack_channel_block_denominator_proven
                ),
            )

        return ExtremeSustainedDPSIndexedFrontierAxis(
            "Structural Family",
            candidate_count=candidate_count,
            candidate_at=candidate_at,
            canonical_axes=("race", "class_route", "attributes"),
        )

    def axis_inventory(self, *, runtime_state_frontier=None):
        axes = tuple(self.pipeline.axes())
        if runtime_state_frontier is not None and runtime_state_frontier_resolver is not None:
            raise ValueError(
                "global generated search accepts either static or candidate-resolved runtime_state, not both"
            )
        if runtime_state_frontier_resolver is not None:
            axes = (
                *axes,
                ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.candidate_axis(
                    runtime_state_frontier_resolver
                ),
            )
        elif runtime_state_frontier is not None:
            axes = (
                *axes,
                ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(
                    runtime_state_frontier
                ),
            )
        return ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
            axes,
            additional_canonical_axes=("race", "class_route", "attributes"),
        )

    def search(
        self,
        *,
        dual_bar_frontier: object,
        candidate_id_prefix: str,
        required_duration_seconds: float,
        potion_cooldown_seconds: float | None,
        starting_ultimate: float,
        priorities: object,
        snapshot_resolver: object,
        target_identity: str,
        runtime_snapshot: object,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
        initial_bar: str = "front",
        ultimate_generation_events: tuple[object, ...] = (),
        heroism_windows: tuple[object, ...] = (),
        use_scheduled_combat_attacks_for_ultimate: bool = False,
        duration_rules: tuple[object, ...] = (),
        heavy_attack_windows: tuple[object, ...] = (),
        heavy_attack_channel_blocks: tuple[object, ...] = (),
        heavy_attack_channel_block_denominator_proven: bool = False,
        root_key: str = "generated-global-root",
        root_bound_inputs=None,
        branch_bound_inputs=None,
        runtime_state_frontier=None,
        runtime_state_frontier_resolver=None,
        potion_cooldown_resolver=None,
        potion_cooldown_scenario=None,
    ):
        prefix = str(candidate_id_prefix or "").strip()
        if not prefix:
            raise ValueError(
                "global generated sustained-DPS search candidate_id_prefix is required"
            )

        structural_axis = self._structural_axis(
            dual_bar_frontier=dual_bar_frontier,
            candidate_id_prefix=prefix,
            duration_seconds=float(required_duration_seconds),
            potion_cooldown_seconds=potion_cooldown_seconds,
            starting_ultimate=float(starting_ultimate),
            priorities=priorities,
            snapshot_resolver=snapshot_resolver,
            target_identity=target_identity,
            ultimate_generation_events=tuple(ultimate_generation_events),
            heroism_windows=tuple(heroism_windows),
            use_scheduled_combat_attacks_for_ultimate=bool(
                use_scheduled_combat_attacks_for_ultimate
            ),
            duration_rules=tuple(duration_rules),
            heavy_attack_windows=tuple(heavy_attack_windows),
            heavy_attack_channel_blocks=tuple(heavy_attack_channel_blocks),
            heavy_attack_channel_block_denominator_proven=bool(
                heavy_attack_channel_block_denominator_proven
            ),
            potion_cooldown_resolver=potion_cooldown_resolver,
            potion_cooldown_scenario=potion_cooldown_scenario,
        )

        axes = (
            structural_axis,
            *tuple(self.pipeline.axes()),
        )
        if runtime_state_frontier is not None:
            axes = (
                *axes,
                ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(
                    runtime_state_frontier
                ),
            )

        evaluate_leaf = self.leaf_evaluation.evaluator(
            runtime_snapshot=runtime_snapshot,
            target_health=int(target_health),
            target_resistance=float(target_resistance),
            target_name=target_name,
            initial_bar=initial_bar,
        )

        return ExtremeSustainedDPSGeneratedFrontierWiringService.search(
            ExtremeSustainedDPSGlobalGeneratedSearchRoot(),
            axes=axes,
            evaluate_leaf=evaluate_leaf,
            required_duration_seconds=float(required_duration_seconds),
            root_key=root_key,
            root_bound_inputs=root_bound_inputs,
            branch_bound_inputs=branch_bound_inputs,
        )


__all__ = [
    "ExtremeSustainedDPSGlobalGeneratedSearchRoot",
    "ExtremeSustainedDPSGlobalGeneratedSearchService",
]
