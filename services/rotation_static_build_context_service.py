from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.build_calculation_context import BuildCalculationContext
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import (
    MinmaxCharacterProgressionAdapter,
    SavedBuildProgressionResolution,
)


@dataclass(frozen=True)
class RotationStaticBuildContextResolution:
    """Canonical static calculation contexts available to one rotation build.

    The contexts reuse the existing MinMax static calculation pipeline, including
    verified armor/passive ownership and rank handling. ``unresolved`` remains
    explicit so later rotation ranking can fail closed rather than applying partial
    static state as though it were complete.
    """

    progression: SavedBuildProgressionResolution
    contexts: tuple[BuildCalculationContext, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.progression.resolved and bool(self.contexts) and not self.unresolved

    def context_for(self, bar: str) -> BuildCalculationContext | None:
        key = str(bar or "").strip().casefold()
        for context in self.contexts:
            if context.active_bar == key:
                return context
        return None

    def maximum_amounts_for(self, resource: ResourceType) -> tuple[tuple[str, int], ...]:
        """Return the canonical maximum resource visible on each resolved bar.

        Bar-sensitive passives can change maximum resources. Keeping the per-bar
        values explicit prevents the rotation engine from silently treating one
        bar's ceiling as globally valid when the current sustain model still accepts
        only one maximum amount for the whole timeline.
        """
        attribute = {
            ResourceType.HEALTH: "max_health",
            ResourceType.MAGICKA: "max_magicka",
            ResourceType.STAMINA: "max_stamina",
        }.get(resource)
        if attribute is None:
            raise ValueError(f"unsupported rotation static resource: {resource!r}")
        return tuple(
            (context.active_bar, int(getattr(context.character_state, attribute)))
            for context in self.contexts
        )

    def uniform_maximum_amount_for(self, resource: ResourceType) -> int | None:
        """Return one safe global maximum when every resolved bar agrees.

        ``None`` means the build is bar-sensitive for this resource and the current
        one-ceiling sustain model must not guess which bar should win.
        """
        values = self.maximum_amounts_for(resource)
        if not values:
            return None
        unique = {amount for _, amount in values}
        if len(unique) != 1:
            return None
        return values[0][1]


class RotationStaticBuildContextService:
    """Resolve front/back static build state for canonical rotation evaluation.

    This service owns no ESO formulas. It deliberately reuses
    ``BuildCalculationContextFactory`` so armor-weight passives, Undaunted Mettle,
    class/guild/weapon passives, static gear, race, CP, food and other already-
    verified inputs keep one source of truth.
    """

    def __init__(
        self,
        *,
        builds_path: str | Path | None = None,
        database_path: str | Path | None = None,
        progression_adapter: MinmaxCharacterProgressionAdapter | None = None,
        context_factory: BuildCalculationContextFactory | None = None,
    ) -> None:
        data_dir = get_data_dir()
        builds = Path(builds_path) if builds_path is not None else data_dir / "builds.json"
        database = Path(database_path) if database_path is not None else data_dir / "eso.db"

        if progression_adapter is None:
            build_service = BuildService(builds)
            progression_adapter = MinmaxCharacterProgressionAdapter(
                build_service.canonical.catalog_service
            )
        if context_factory is None:
            context_factory = BuildCalculationContextFactory(
                race_repository=RaceRepository(database),
                gear_set_repository=GearSetRepository(database),
            )

        self.progression_adapter = progression_adapter
        self.context_factory = context_factory

    def resolve(
        self,
        player_build: PlayerBuild,
        *,
        bars: tuple[str, ...] = ("front", "back"),
    ) -> RotationStaticBuildContextResolution:
        requested = self._normalize_bars(bars)
        progression = self.progression_adapter.resolve(player_build)
        if not progression.resolved:
            return RotationStaticBuildContextResolution(
                progression=progression,
                contexts=(),
                unresolved=self._dedupe(tuple(progression.unresolved)),
            )

        build_id = (
            str(getattr(player_build, "BuildId", "") or "").strip()
            or str(getattr(player_build, "BuildName", "") or "").strip()
            or "rotation-build"
        )
        contexts: list[BuildCalculationContext] = []
        unresolved: list[str] = []
        for bar in requested:
            context = self.context_factory.build(
                character_id=progression.character_id,
                build_id=build_id,
                build=player_build,
                progression=progression.progression,
                active_bar=bar,
            )
            contexts.append(context)
            unresolved.extend(
                f"{bar} static context: {message}"
                for message in context.unresolved_gear_effects
                if str(message or "").strip()
            )

        return RotationStaticBuildContextResolution(
            progression=progression,
            contexts=tuple(contexts),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _normalize_bars(bars: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in bars:
            value = str(raw or "").strip().casefold()
            if value not in {"front", "back"}:
                raise ValueError("rotation static context bar must be front or back")
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        if not result:
            raise ValueError("rotation static context requires at least one bar")
        return tuple(result)

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw or "").strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationStaticBuildContextResolution",
    "RotationStaticBuildContextService",
]
