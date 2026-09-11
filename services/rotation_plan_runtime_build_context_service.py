from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from minmax.build_calculation_context import BuildCalculationContext
from models.build_model import PlayerBuild
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateResult,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService


class RotationRuntimeCombatStateResolver(Protocol):
    def __call__(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> RotationPlanRuntimeCombatStateResult: ...


@dataclass(frozen=True)
class RotationPlanRuntimeBuildContextResult:
    """One exact rebuilt calculation context for a runtime point in a rotation."""

    time_seconds: float
    sequence: int | None
    active_bar: str
    context: BuildCalculationContext | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.context is not None and not self.unresolved


class RotationPlanRuntimeBuildContextService:
    """Rebuild canonical active-bar calculation state at an exact runtime instant.

    ``RotationPlanRuntimeCombatStateService`` remains authoritative for temporal
    runtime truth and bar identity. This bridge deliberately rebuilds the selected
    bar through ``RotationStaticBuildContextService`` instead of merely replacing
    ``BuildCalculationContext.combat_state`` on an old static context. Derived
    ``character_state``/``core_state`` values can depend on transient named buffs,
    so stale static state would produce internally inconsistent healer/damage math.
    """

    def __init__(
        self,
        *,
        static_context_service: RotationStaticBuildContextService,
    ) -> None:
        self.static_context_service = static_context_service

    def resolve(
        self,
        build: PlayerBuild,
        *,
        runtime_combat_state_resolver: RotationRuntimeCombatStateResolver,
        time_seconds: float,
        sequence: int | None = None,
    ) -> RotationPlanRuntimeBuildContextResult:
        runtime = runtime_combat_state_resolver(time_seconds, sequence)
        if not runtime.resolved or runtime.combat_state is None:
            unresolved = tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in runtime.unresolved
                    if str(message).strip()
                )
            )
            if not unresolved:
                unresolved = (
                    "runtime combat state is unresolved for exact build-context projection",
                )
            return RotationPlanRuntimeBuildContextResult(
                time_seconds=float(runtime.time_seconds),
                sequence=runtime.sequence,
                active_bar=str(runtime.active_bar),
                context=None,
                unresolved=unresolved,
            )

        rebuilt = self.static_context_service.resolve(
            build,
            bars=(runtime.active_bar,),
            combat_state=runtime.combat_state,
        )
        unresolved = tuple(
            dict.fromkeys(
                str(message).strip()
                for message in rebuilt.unresolved
                if str(message).strip()
            )
        )
        context = rebuilt.context_for(runtime.active_bar) if rebuilt.resolved else None
        if context is None and not unresolved:
            unresolved = (
                f"runtime build context is missing the {runtime.active_bar} bar",
            )

        return RotationPlanRuntimeBuildContextResult(
            time_seconds=float(runtime.time_seconds),
            sequence=runtime.sequence,
            active_bar=str(runtime.active_bar),
            context=None if unresolved else context,
            unresolved=unresolved,
        )


__all__ = [
    "RotationPlanRuntimeBuildContextResult",
    "RotationPlanRuntimeBuildContextService",
    "RotationRuntimeCombatStateResolver",
]
