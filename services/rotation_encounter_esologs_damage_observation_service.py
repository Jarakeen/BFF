from __future__ import annotations

"""Read-only ESO Logs candidate extraction for encounter damage mechanics."""

from dataclasses import dataclass
from typing import Protocol

from services.esologs_event_interpreter import SemanticCombatEvent, SemanticEventKind


class RotationEncounterEsoLogsEventSource(Protocol):
    def iter_fight(
        self,
        report_code: str,
        fight_id: int,
        *,
        event_kinds: set[str] | None = None,
    ): ...


@dataclass(frozen=True)
class RotationEncounterDamageObservationTarget:
    """Explicit observational aliases for one canonical encounter mechanic.

    The canonical lower-snake-case mechanic id owns semantic identity. Numeric ability
    ids and display names are observation aliases only and are intentionally separated
    for cast and damage streams because ESO can emit different ids for one mechanic.
    """

    canonical_mechanic_id: str
    cast_ability_game_ids: tuple[int, ...] = ()
    cast_ability_names: tuple[str, ...] = ()
    damage_ability_game_ids: tuple[int, ...] = ()
    damage_ability_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationEncounterDamageObservationCandidate:
    canonical_mechanic_id: str
    cast_event_index: int
    cast_time_seconds: float
    first_damage_time_seconds: float
    last_damage_time_seconds: float
    logical_damage_tick_times_seconds: tuple[float, ...]
    logical_damage_tick_offsets_seconds: tuple[float, ...]
    cadence_intervals_seconds: tuple[float, ...]
    target_ids: tuple[int, ...]
    observed_target_count: int
    raw_damage_event_count: int
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class RotationEncounterDamageObservationReport:
    report_code: str
    fight_id: int
    target: RotationEncounterDamageObservationTarget
    candidates: tuple[RotationEncounterDamageObservationCandidate, ...]
    unresolved: tuple[str, ...] = ()


class RotationEncounterEsoLogsDamageObservationService:
    """Extract review candidates for encounter-damage cadence and target scope.

    This service never promotes mechanic timing or target counts. It requires explicit
    observational aliases, anchors damage to matching cast events, and reports only what
    the selected fight actually emitted. Damage belonging to one cast is bounded by the
    next matching cast, so no arbitrary episode-gap threshold is invented.
    """

    def __init__(self, event_source: RotationEncounterEsoLogsEventSource) -> None:
        self.event_source = event_source

    def observe(
        self,
        *,
        report_code: str,
        fight_id: int,
        target: RotationEncounterDamageObservationTarget,
        timestamp_scale: float = 0.001,
        recipient_tick_merge_tolerance_seconds: float = 0.05,
    ) -> RotationEncounterDamageObservationReport:
        canonical_id = str(target.canonical_mechanic_id or "").strip().casefold()
        if not canonical_id:
            raise ValueError("encounter damage observation requires canonical_mechanic_id")
        if canonical_id != target.canonical_mechanic_id:
            raise ValueError("canonical encounter mechanic identity must be lower_snake_case")
        scale = float(timestamp_scale)
        if scale <= 0:
            raise ValueError("timestamp_scale must be positive")
        merge_tolerance = float(recipient_tick_merge_tolerance_seconds)
        if merge_tolerance < 0:
            raise ValueError("recipient tick merge tolerance must be non-negative")
        if not (target.cast_ability_game_ids or target.cast_ability_names):
            raise ValueError("encounter damage observation requires explicit cast aliases")
        if not (target.damage_ability_game_ids or target.damage_ability_names):
            raise ValueError("encounter damage observation requires explicit damage aliases")

        events = tuple(
            self.event_source.iter_fight(
                str(report_code),
                int(fight_id),
                event_kinds={SemanticEventKind.CAST, SemanticEventKind.DAMAGE},
            )
        )
        casts = tuple(
            event
            for event in events
            if event.event_kind == SemanticEventKind.CAST
            and self._matches(
                event,
                ability_game_ids=target.cast_ability_game_ids,
                ability_names=target.cast_ability_names,
            )
        )
        if not casts:
            return RotationEncounterDamageObservationReport(
                report_code=str(report_code),
                fight_id=int(fight_id),
                target=target,
                candidates=(),
                unresolved=(
                    f"{canonical_id}: no matching cast event across explicit observation aliases",
                ),
            )

        candidates: list[RotationEncounterDamageObservationCandidate] = []
        unresolved: list[str] = []
        for index, cast in enumerate(casts):
            cast_time = float(cast.timestamp) * scale
            next_cast_time = (
                float(casts[index + 1].timestamp) * scale
                if index + 1 < len(casts)
                else None
            )
            damage_events = tuple(
                event
                for event in events
                if event.event_kind == SemanticEventKind.DAMAGE
                and self._matches(
                    event,
                    ability_game_ids=target.damage_ability_game_ids,
                    ability_names=target.damage_ability_names,
                )
                and (cast.source_id is None or event.source_id == cast.source_id)
                and float(event.timestamp) * scale >= cast_time
                and (
                    next_cast_time is None
                    or float(event.timestamp) * scale < next_cast_time
                )
            )
            if not damage_events:
                unresolved.append(
                    f"{canonical_id} cast event {cast.event_index}: no matching damage events before next cast"
                )
                continue

            raw_times = tuple(float(event.timestamp) * scale for event in damage_events)
            logical_ticks = self._collapse_recipient_tick_times(
                raw_times,
                merge_tolerance_seconds=merge_tolerance,
            )
            offsets = tuple(round(value - cast_time, 6) for value in logical_ticks)
            cadence = tuple(
                round(current - previous, 6)
                for previous, current in zip(logical_ticks, logical_ticks[1:])
            )
            target_ids = tuple(
                sorted(
                    {
                        int(event.target_id)
                        for event in damage_events
                        if event.target_id is not None
                        and event.target_is_friendly is not False
                    }
                )
            )
            candidates.append(
                RotationEncounterDamageObservationCandidate(
                    canonical_mechanic_id=canonical_id,
                    cast_event_index=int(cast.event_index),
                    cast_time_seconds=round(cast_time, 6),
                    first_damage_time_seconds=logical_ticks[0],
                    last_damage_time_seconds=logical_ticks[-1],
                    logical_damage_tick_times_seconds=logical_ticks,
                    logical_damage_tick_offsets_seconds=offsets,
                    cadence_intervals_seconds=cadence,
                    target_ids=target_ids,
                    observed_target_count=len(target_ids),
                    raw_damage_event_count=len(damage_events),
                    provenance=(
                        f"candidate extracted from ESO Logs report {report_code} fight {int(fight_id)}",
                        f"canonical_mechanic_id={canonical_id} cast_event_index={int(cast.event_index)}",
                        "explicit cast/damage aliases only; candidate evidence is not promoted to canonical mechanic policy",
                    ),
                )
            )

        return RotationEncounterDamageObservationReport(
            report_code=str(report_code),
            fight_id=int(fight_id),
            target=target,
            candidates=tuple(candidates),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _matches(
        event: SemanticCombatEvent,
        *,
        ability_game_ids: tuple[int, ...],
        ability_names: tuple[str, ...],
    ) -> bool:
        ids = {int(value) for value in ability_game_ids}
        names = {str(value).strip().casefold() for value in ability_names if str(value).strip()}
        id_match = event.ability_game_id is not None and int(event.ability_game_id) in ids
        name_match = (
            event.ability_name is not None
            and str(event.ability_name).strip().casefold() in names
        )
        return id_match or name_match

    @staticmethod
    def _collapse_recipient_tick_times(
        timestamps,
        *,
        merge_tolerance_seconds: float,
    ) -> tuple[float, ...]:
        ordered = sorted(float(value) for value in timestamps)
        collapsed: list[float] = []
        cluster_start: float | None = None
        for value in ordered:
            if cluster_start is None or value - cluster_start > merge_tolerance_seconds:
                cluster_start = value
                collapsed.append(round(value, 6))
        return tuple(collapsed)


__all__ = [
    "RotationEncounterDamageObservationCandidate",
    "RotationEncounterDamageObservationReport",
    "RotationEncounterDamageObservationTarget",
    "RotationEncounterEsoLogsDamageObservationService",
]
