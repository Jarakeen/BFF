from __future__ import annotations

"""Inventory active named-gear bonus semantics for sustained-DPS runtime scoring."""

from dataclasses import dataclass
from enum import Enum

from minmax.gear_set_activation_rules import active_item_set_bonus_counts
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_known_effects import known_effects_for_bonus_row
from minmax.gear_set_repository import GearSetRepository
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState


class ExtremeSustainedDPSGearSemanticKind(str, Enum):
    STATIC = "static"
    CONDITIONAL_STATIC = "conditional_static"
    RUNTIME = "runtime"
    STATIC_AND_RUNTIME = "static_and_runtime"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ExtremeSustainedDPSGearBonusSemantic:
    bar: str
    set_id: int
    set_name: str
    piece_count: int
    bonus_id: int
    kind: ExtremeSustainedDPSGearSemanticKind
    static_effect_count: int
    runtime_variant_count: int
    runtime_evaluation_required: bool
    description: str


@dataclass(frozen=True)
class ExtremeSustainedDPSGearRuntimeSemanticInventory:
    rows: tuple[ExtremeSustainedDPSGearBonusSemantic, ...]
    static_row_count: int
    conditional_static_row_count: int
    runtime_row_count: int
    mixed_row_count: int
    unsupported_row_count: int
    semantic_mapping_complete: bool
    runtime_evaluation_required: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSGearRuntimeSemanticInventoryService:
    """Classify active set bonuses without inventing unsupported runtime mechanics."""

    def __init__(
        self,
        repository: GearSetRepository | object,
        *,
        static_resolver: GearSetEffectResolver | None = None,
    ) -> None:
        self.repository = repository
        self.static_resolver = static_resolver or GearSetEffectResolver()

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSGearRuntimeSemanticInventoryService":
        return cls(GearSetRepository(database_path))

    def inventory(
        self,
        state: ExtremeDualBarGearState,
    ) -> ExtremeSustainedDPSGearRuntimeSemanticInventory:
        rows: list[ExtremeSustainedDPSGearBonusSemantic] = []
        unresolved: list[str] = []

        for bar, realization in (("front", state.front), ("back", state.back)):
            set_identity = {
                str(name): (int(set_id), int(count))
                for set_id, name, count in zip(
                    realization.set_ids,
                    realization.set_names,
                    realization.counts,
                )
            }
            active_counts = active_item_set_bonus_counts(
                {name: count for name, (_set_id, count) in set_identity.items()}
            )

            for set_name, equipped_count in sorted(
                active_counts.items(),
                key=lambda item: item[0].casefold(),
            ):
                identity = set_identity.get(set_name)
                if identity is None:
                    unresolved.append(
                        f"{bar}: active set identity disappeared during semantic inventory: {set_name}"
                    )
                    continue
                set_id, _ = identity

                for bonus in self.repository.get_bonuses(set_id):
                    if int(bonus.piece_count) > int(equipped_count):
                        continue

                    source = f"{set_name} ({int(bonus.piece_count)})"
                    static_effects = tuple(
                        self.static_resolver.resolve(
                            bonus,
                            use_max_value=True,
                            source=source,
                        )
                    )
                    runtime_variants = tuple(
                        known_effects_for_bonus_row(
                            int(bonus.id),
                            int(bonus.set_id),
                            set_name,
                            int(bonus.piece_count),
                        )
                    )
                    has_conditional_static = any(
                        str(getattr(effect, "condition", "") or "").strip()
                        for effect in static_effects
                    )

                    if static_effects and runtime_variants:
                        kind = ExtremeSustainedDPSGearSemanticKind.STATIC_AND_RUNTIME
                    elif static_effects and has_conditional_static:
                        kind = ExtremeSustainedDPSGearSemanticKind.CONDITIONAL_STATIC
                    elif static_effects:
                        kind = ExtremeSustainedDPSGearSemanticKind.STATIC
                    elif runtime_variants:
                        kind = ExtremeSustainedDPSGearSemanticKind.RUNTIME
                    else:
                        kind = ExtremeSustainedDPSGearSemanticKind.UNSUPPORTED
                        unresolved.append(
                            f"{bar}: {source} active set bonus is not mapped by the reviewed static resolver or verified runtime-effect registry"
                        )

                    rows.append(
                        ExtremeSustainedDPSGearBonusSemantic(
                            bar=bar,
                            set_id=set_id,
                            set_name=set_name,
                            piece_count=int(bonus.piece_count),
                            bonus_id=int(bonus.id),
                            kind=kind,
                            static_effect_count=len(static_effects),
                            runtime_variant_count=len(runtime_variants),
                            runtime_evaluation_required=bool(
                                runtime_variants or has_conditional_static
                            ),
                            description=str(bonus.description or "").strip(),
                        )
                    )

        ordered = tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.bar,
                    row.set_name.casefold(),
                    row.set_id,
                    row.piece_count,
                    row.bonus_id,
                ),
            )
        )
        static_count = sum(
            row.kind is ExtremeSustainedDPSGearSemanticKind.STATIC
            for row in ordered
        )
        conditional_count = sum(
            row.kind is ExtremeSustainedDPSGearSemanticKind.CONDITIONAL_STATIC
            for row in ordered
        )
        runtime_count = sum(
            row.kind is ExtremeSustainedDPSGearSemanticKind.RUNTIME
            for row in ordered
        )
        mixed_count = sum(
            row.kind is ExtremeSustainedDPSGearSemanticKind.STATIC_AND_RUNTIME
            for row in ordered
        )
        unsupported_count = sum(
            row.kind is ExtremeSustainedDPSGearSemanticKind.UNSUPPORTED
            for row in ordered
        )
        runtime_required = any(row.runtime_evaluation_required for row in ordered)
        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))

        return ExtremeSustainedDPSGearRuntimeSemanticInventory(
            rows=ordered,
            static_row_count=static_count,
            conditional_static_row_count=conditional_count,
            runtime_row_count=runtime_count,
            mixed_row_count=mixed_count,
            unsupported_row_count=unsupported_count,
            semantic_mapping_complete=not final_unresolved and unsupported_count == 0,
            runtime_evaluation_required=runtime_required,
            evidence=(
                f"Active gear bonus rows reviewed across both bars: {len(ordered)}",
                f"Static rows: {static_count}",
                f"Conditional-static rows: {conditional_count}",
                f"Verified runtime rows: {runtime_count}",
                f"Static + runtime rows: {mixed_count}",
                f"Unsupported active rows: {unsupported_count}",
                "Runtime-mapped identity does not prove trigger occurrence, uptime, proc cadence, or sustained-DPS contribution",
            ),
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSGearBonusSemantic",
    "ExtremeSustainedDPSGearRuntimeSemanticInventory",
    "ExtremeSustainedDPSGearRuntimeSemanticInventoryService",
    "ExtremeSustainedDPSGearSemanticKind",
]
