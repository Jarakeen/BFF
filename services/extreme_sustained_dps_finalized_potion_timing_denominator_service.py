from __future__ import annotations

"""Compose finalized DD observations with canonical potion timing mechanics."""

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_potion_observation_frontier_service import (
    ExtremeSustainedDPSPotionObservationFrontier,
)
from services.extreme_sustained_dps_potion_timing_breakpoint_frontier_service import (
    ExtremeSustainedDPSPotionTimingBreakpointFrontier,
    ExtremeSustainedDPSPotionTimingBreakpointFrontierService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSFinalizedPotionTimingDenominator:
    observation_frontier: ExtremeSustainedDPSPotionObservationFrontier
    breakpoint_frontier: ExtremeSustainedDPSPotionTimingBreakpointFrontier
    effective_buff_durations: tuple[float, ...]
    denominator_proven: bool
    omitted_scope: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSFinalizedPotionTimingDenominatorService:
    """Prove finite named-buff timing denominator for one finalized descendant."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        event_resolver: PotionUseEventResolver | None = None,
    ) -> None:
        database = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.event_resolver = event_resolver or PotionUseEventResolver(
            database_path=database
        )

    def build(
        self,
        *,
        player_build: PlayerBuild,
        progression: CharacterProgression,
        observation_frontier: ExtremeSustainedDPSPotionObservationFrontier,
        duration_seconds: float,
        cooldown_seconds: float,
        instant_restoration_timing_closed: bool = False,
        resource_observation_times: tuple[float, ...] = (),
        resource_observation_denominator_proven: bool = False,
    ) -> ExtremeSustainedDPSFinalizedPotionTimingDenominator:
        if not isinstance(instant_restoration_timing_closed, bool):
            raise TypeError("instant_restoration_timing_closed must be boolean")
        if not isinstance(resource_observation_denominator_proven, bool):
            raise TypeError("resource_observation_denominator_proven must be boolean")
        if not isinstance(resource_observation_times, tuple):
            raise TypeError("resource_observation_times must be a tuple")

        unresolved = list(observation_frontier.unresolved)
        normalized_resource_times: list[float] = []
        for value in resource_observation_times:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("resource_observation_times must contain only numbers")
            normalized_resource_times.append(float(value))
        resource_times = tuple(sorted(set(normalized_resource_times)))
        if resource_times and not resource_observation_denominator_proven:
            unresolved.append(
                "Potion resource observation times were supplied without denominator proof"
            )
        restoration_closed = bool(
            instant_restoration_timing_closed
            or resource_observation_denominator_proven
        )
        combined_observation_times = tuple(
            sorted(
                {
                    *tuple(observation_frontier.observation_times),
                    *resource_times,
                }
            )
        )
        potion_name = " ".join(
            str(getattr(player_build, "Potion", "") or "").strip().split()
        )
        if not potion_name:
            unresolved.append(
                "Finalized potion timing denominator requires a saved potion selection"
            )
            empty = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
                duration_seconds=duration_seconds,
                cooldown_seconds=cooldown_seconds,
                observation_times=combined_observation_times,
                effective_buff_durations=(),
                instant_restoration_timing_closed=restoration_closed,
            )
            return ExtremeSustainedDPSFinalizedPotionTimingDenominator(
                observation_frontier=observation_frontier,
                breakpoint_frontier=empty,
                effective_buff_durations=(),
                denominator_proven=False,
                omitted_scope=tuple(empty.omitted_scope),
                evidence=tuple(observation_frontier.evidence),
                unresolved=tuple(dict.fromkeys(unresolved + list(empty.unresolved))),
            )

        rank = progression.passive_rank("Medicinal Use")
        if rank is None:
            unresolved.append(
                "Medicinal Use rank is unresolved for finalized potion timing denominator"
            )

        event = self.event_resolver.resolve(potion_name)
        unresolved.extend(tuple(event.unresolved))

        durations: tuple[float, ...] = ()
        if rank is not None and event.resolved:
            try:
                if isinstance(rank, bool) or not isinstance(rank, int):
                    raise TypeError("Medicinal Use rank must be an integer")
                if isinstance(cooldown_seconds, bool) or not isinstance(cooldown_seconds, (int, float)):
                    raise TypeError("cooldown_seconds must be numeric")
                cadence = PotionCadence(
                    event,
                    medicinal_use_rank=rank,
                    cooldown_seconds=float(cooldown_seconds),
                )
            except ValueError as exc:
                unresolved.append(str(exc))
            else:
                durations = tuple(
                    sorted(
                        {
                            float(cadence.effective_duration(grant))
                            for grant in event.buff_grants
                        }
                    )
                )
                if not durations:
                    unresolved.append(
                        "Resolved potion supplies no canonical named-buff durations"
                    )

        breakpoint = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
            duration_seconds=duration_seconds,
            cooldown_seconds=cooldown_seconds,
            observation_times=combined_observation_times,
            effective_buff_durations=durations,
            instant_restoration_timing_closed=restoration_closed,
        )
        unresolved.extend(tuple(breakpoint.unresolved))
        deduped = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )

        proven = bool(
            observation_frontier.denominator_proven
            and breakpoint.named_buff_state_denominator_proven
            and not deduped
        )

        return ExtremeSustainedDPSFinalizedPotionTimingDenominator(
            observation_frontier=observation_frontier,
            breakpoint_frontier=breakpoint,
            effective_buff_durations=durations,
            denominator_proven=proven,
            omitted_scope=tuple(breakpoint.omitted_scope),
            evidence=(
                *tuple(observation_frontier.evidence),
                f"Canonical effective potion buff durations: {len(durations)}",
                f"Caller-proven resource observation timestamps: {len(resource_times)}",
                (
                    "Potion instant-restoration timing denominator proven"
                    if restoration_closed
                    else "Potion instant-restoration timing denominator remains open"
                ),
                *tuple(breakpoint.evidence),
                (
                    "Finalized named-buff potion timing denominator proven"
                    if proven
                    else "Finalized named-buff potion timing denominator remains open"
                ),
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSFinalizedPotionTimingDenominator",
    "ExtremeSustainedDPSFinalizedPotionTimingDenominatorService",
]
