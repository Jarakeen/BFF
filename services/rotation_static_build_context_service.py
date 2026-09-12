from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from minmax.build_calculation_context import BuildCalculationContext
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceMaximumEvent
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import (
    MinmaxCharacterProgressionAdapter,
    SavedBuildProgressionResolution,
)
from services.rotation_saved_build_charged_status_chance_service import (
    RotationSavedBuildChargedStatusChanceService,
)
from services.rotation_saved_build_dd_conditional_damage_done_service import (
    RotationSavedBuildDDConditionalDamageDoneService,
)
from services.rotation_saved_build_dd_damage_done_service import (
    RotationSavedBuildDDDamageDoneService,
)


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}
_EXPLOITER_UNMODELED_PREFIX = "champion point effect not yet modeled: exploiter:"


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

    @staticmethod
    def _resource_attribute(resource: ResourceType) -> str:
        attribute = {
            ResourceType.HEALTH: "max_health",
            ResourceType.MAGICKA: "max_magicka",
            ResourceType.STAMINA: "max_stamina",
        }.get(resource)
        if attribute is None:
            raise ValueError(f"unsupported rotation static resource: {resource!r}")
        return attribute

    @staticmethod
    def _recovery_attribute(resource: ResourceType) -> str:
        attribute = {
            ResourceType.HEALTH: "health_recovery",
            ResourceType.MAGICKA: "magicka_recovery",
            ResourceType.STAMINA: "stamina_recovery",
        }.get(resource)
        if attribute is None:
            raise ValueError(f"unsupported rotation static resource recovery: {resource!r}")
        return attribute

    def maximum_amounts_for(self, resource: ResourceType) -> tuple[tuple[str, int], ...]:
        """Return the canonical maximum resource visible on each resolved bar."""
        attribute = self._resource_attribute(resource)
        return tuple(
            (context.active_bar, int(getattr(context.character_state, attribute)))
            for context in self.contexts
        )

    def maximum_amount_for(self, bar: str, resource: ResourceType) -> int:
        context = self.context_for(bar)
        if context is None:
            raise ValueError(f"rotation static context is missing bar: {bar!r}")
        return int(getattr(context.character_state, self._resource_attribute(resource)))

    def displayed_recovery_amounts_for(
        self,
        resource: ResourceType,
    ) -> tuple[tuple[str, int], ...]:
        """Return canonical character-sheet recovery visible on each resolved bar."""
        attribute = self._recovery_attribute(resource)
        return tuple(
            (context.active_bar, int(getattr(context.character_state, attribute)))
            for context in self.contexts
        )

    def displayed_recovery_for(self, bar: str, resource: ResourceType) -> int:
        context = self.context_for(bar)
        if context is None:
            raise ValueError(f"rotation static context is missing bar: {bar!r}")
        return int(getattr(context.character_state, self._recovery_attribute(resource)))

    def uniform_maximum_amount_for(self, resource: ResourceType) -> int | None:
        """Return one safe global maximum when every resolved bar agrees."""
        values = self.maximum_amounts_for(resource)
        if not values:
            return None
        unique = {amount for _, amount in values}
        if len(unique) != 1:
            return None
        return values[0][1]

    def maximum_events_for(
        self,
        plan: RotationPlan,
        resource: ResourceType,
        *,
        initial_bar: str = "front",
    ) -> tuple[ResourceMaximumEvent, ...]:
        """Project bar swaps into verified resource-ceiling transitions."""
        current_bar = str(initial_bar or "").strip().casefold()
        if current_bar not in {"front", "back"}:
            raise ValueError("rotation static initial bar must be front or back")
        current_maximum = self.maximum_amount_for(current_bar, resource)

        events: list[ResourceMaximumEvent] = []
        for action in plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            destination = str(action.bar or "").strip().casefold()
            if destination not in {"front", "back"}:
                raise ValueError("bar-swap rotation action requires a valid destination bar")
            destination_maximum = self.maximum_amount_for(destination, resource)
            current_bar = destination
            if destination_maximum == current_maximum:
                continue
            events.append(
                ResourceMaximumEvent(
                    time_seconds=float(action.time_seconds),
                    resource=resource,
                    maximum=destination_maximum,
                    source=(
                        f"Bar swap to {destination}: canonical {resource.value} maximum"
                    ),
                )
            )
            current_maximum = destination_maximum
        return tuple(events)

    def displayed_recovery_resolver_for(
        self,
        plan: RotationPlan,
        resource: ResourceType,
        *,
        initial_bar: str = "front",
    ) -> Callable[[float], int]:
        """Resolve canonical displayed recovery from the bar active at each instant.

        A bar swap at the exact time of a recovery tick activates the destination
        bar first, matching the resource timeline's destination-bar-first ordering.
        """
        starting_bar = str(initial_bar or "").strip().casefold()
        if starting_bar not in {"front", "back"}:
            raise ValueError("rotation static initial bar must be front or back")
        self.displayed_recovery_for(starting_bar, resource)

        swaps: list[tuple[float, int, str]] = []
        for action in plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            destination = str(action.bar or "").strip().casefold()
            if destination not in {"front", "back"}:
                raise ValueError("bar-swap rotation action requires a valid destination bar")
            self.displayed_recovery_for(destination, resource)
            swaps.append((float(action.time_seconds), int(action.sequence), destination))
        swaps.sort(key=lambda item: (item[0], item[1]))

        def resolve(time_seconds: float) -> int:
            instant = float(time_seconds)
            if instant < 0:
                raise ValueError("displayed recovery lookup time cannot be negative")
            active_bar = starting_bar
            for swap_time, _sequence, destination in swaps:
                if swap_time > instant:
                    break
                active_bar = destination
            return self.displayed_recovery_for(active_bar, resource)

        return resolve


class RotationStaticBuildContextService:
    """Resolve front/back static build state for canonical rotation evaluation.

    This service owns no ESO formulas. It deliberately reuses
    ``BuildCalculationContextFactory`` so armor-weight passives, Undaunted Mettle,
    class/guild/weapon passives, static gear, race, CP, food and other already-
    verified inputs keep one source of truth. Reviewed unconditional DD Damage Done,
    conditional Exploiter magnitude, and reviewed Charged status-chance magnitude are
    attached as context metadata rather than flattened into standing-sheet stats.
    """

    def __init__(
        self,
        *,
        builds_path: str | Path | None = None,
        database_path: str | Path | None = None,
        progression_adapter: MinmaxCharacterProgressionAdapter | None = None,
        context_factory: BuildCalculationContextFactory | None = None,
        dd_damage_done_service: RotationSavedBuildDDDamageDoneService | None = None,
        dd_conditional_damage_done_service: (
            RotationSavedBuildDDConditionalDamageDoneService | None
        ) = None,
        charged_status_chance_service: (
            RotationSavedBuildChargedStatusChanceService | None
        ) = None,
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
        self.dd_damage_done_service = (
            dd_damage_done_service or RotationSavedBuildDDDamageDoneService(database)
        )
        self.dd_conditional_damage_done_service = (
            dd_conditional_damage_done_service
            or RotationSavedBuildDDConditionalDamageDoneService(database)
        )
        self.charged_status_chance_service = (
            charged_status_chance_service
            or RotationSavedBuildChargedStatusChanceService(database)
        )

    def resolve(
        self,
        player_build: PlayerBuild,
        *,
        bars: tuple[str, ...] = ("front", "back"),
        combat_state: CombatState = CombatState(),
    ) -> RotationStaticBuildContextResolution:
        requested = self._normalize_bars(bars)
        progression = self.progression_adapter.resolve(player_build)
        if not progression.resolved:
            return RotationStaticBuildContextResolution(
                progression=progression,
                contexts=(),
                unresolved=self._dedupe(tuple(progression.unresolved)),
            )

        role_key = " ".join(
            str(getattr(player_build, "Role", "") or "").strip().casefold().split()
        )
        dd_damage_done = None
        dd_exploiter_bonus = 0.0
        dd_conditional_resolved = False
        charged_resolution = None
        charged_messages_by_bar: dict[str, set[str]] = {"front": set(), "back": set()}
        dd_unresolved: list[str] = []
        if role_key in _DD_ROLE_KEYS:
            dd_resolution = self.dd_damage_done_service.resolve(player_build)
            dd_damage_done = dd_resolution.modifiers
            dd_unresolved.extend(dd_resolution.unresolved)
            conditional = self.dd_conditional_damage_done_service.resolve(player_build)
            dd_exploiter_bonus = float(conditional.exploiter_bonus)
            dd_conditional_resolved = conditional.resolved
            dd_unresolved.extend(conditional.unresolved)
            charged_resolution = self.charged_status_chance_service.resolve(
                player_build,
                bars=requested,
            )
            dd_unresolved.extend(charged_resolution.unresolved)
            if charged_resolution.resolved:
                for source in charged_resolution.sources:
                    charged_messages_by_bar[source.bar].add(
                        f"{source.slot_name} Charged: requires status-effect chance model".casefold()
                    )

        build_id = (
            str(getattr(player_build, "BuildId", "") or "").strip()
            or str(getattr(player_build, "BuildName", "") or "").strip()
            or "rotation-build"
        )
        contexts: list[BuildCalculationContext] = []
        unresolved: list[str] = list(dd_unresolved)
        for bar in requested:
            context = self.context_factory.build(
                character_id=progression.character_id,
                build_id=build_id,
                build=player_build,
                progression=progression.progression,
                active_bar=bar,
                combat_state=combat_state,
            )
            if dd_damage_done is not None:
                charged_bonus = (
                    charged_resolution.bonus_percent_for(bar)
                    if charged_resolution is not None and charged_resolution.resolved
                    else 0.0
                )
                context = replace(
                    context,
                    dd_damage_done_modifiers=dd_damage_done,
                    dd_exploiter_bonus=dd_exploiter_bonus,
                    dd_status_effect_chance_bonus_percent=charged_bonus,
                )
            contexts.append(context)
            unresolved.extend(
                f"{bar} static context: {message}"
                for message in context.unresolved_gear_effects
                if str(message or "").strip()
                and not (
                    dd_conditional_resolved
                    and str(message or "").strip().casefold().startswith(
                        _EXPLOITER_UNMODELED_PREFIX
                    )
                )
                and str(message or "").strip().casefold()
                not in charged_messages_by_bar.get(bar, set())
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
