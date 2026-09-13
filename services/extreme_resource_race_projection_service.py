from __future__ import annotations

"""Proof-reduce legal races for Extreme max-resource scoring.

The complete legal race universe remains the denominator.  For a scalar maximum
resource objective, every legal race is first resolved through the same canonical
racial progression and tooltip parser used by final scoring.  When all target-resource
contributions are complete and non-negative, only the legal race with the largest
canonical target-resource contribution can win the maximum objective.

This is an objective-dominance reduction, not an assertion that races are generally
equivalent. Non-target racial stats remain owned by the canonical racial resolver and
cannot make a smaller static target-resource contribution exceed a larger one for the
instantaneous Max Health/Magicka/Stamina objective. Any unresolved or invalid racial
evidence disables the reduction so the generic structural search falls back to the
full race universe.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.racial_passive_stat_repository import RacialPassiveStatRepository
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)


_SUPPORTED_OBJECTIVES = frozenset({"max_health", "max_magicka", "max_stamina"})


@dataclass(frozen=True)
class ExtremeResourceRaceProjection:
    objective_key: str
    source_race_count: int
    races: tuple[str, ...]
    signatures: tuple[float, ...]
    source_signatures: tuple[tuple[str, float], ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.denominator_proven
            and self.source_race_count > 0
            and len(self.races) == 1
            and len(self.signatures) == 1
            and len(self.source_signatures) == self.source_race_count
            and not self.unresolved
        )

    @property
    def scope(self) -> tuple[str, ...]:
        if not self.projection_complete:
            return ()
        witness = self.races[0]
        value = self.signatures[0]
        return (
            "legal races proof-reduced by complete canonical target-resource dominance; "
            f"{self.source_race_count} legal races -> 1 maximum witness "
            f"({witness}: {value:g})",
        )


class ExtremeResourceRaceProjectionService:
    """Retain the strongest legal canonical target-resource racial witness."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path,
        *,
        progression_service: ExtremeHypotheticalRacialProgressionService | None = None,
        racial_repository: RacialPassiveStatRepository | None = None,
    ) -> None:
        self.progression_service = progression_service or (
            ExtremeHypotheticalRacialProgressionService(database_path)
        )
        self.racial_repository = racial_repository or RacialPassiveStatRepository(database_path)

    def _signature(self, race: str, objective_key: str) -> tuple[float | None, tuple[str, ...]]:
        try:
            progression = self.progression_service.normalize(CharacterProgression(), race)
            canonical_race = self.progression_service._canonical_skill_line_race(race)
            resolution = self.racial_repository.resolve(canonical_race, progression)
        except Exception as exc:
            return None, (
                f"Canonical racial projection failed for {race}: {type(exc).__name__}: {exc}",
            )

        if resolution.unresolved:
            return None, tuple(
                f"{race}: {message}" for message in resolution.unresolved if str(message)
            )

        try:
            value = float(resolution.stats.get(objective_key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return None, (f"Canonical racial target-resource value is invalid for {race}",)
        if value < -1e-9:
            return None, (
                f"Canonical racial target-resource value is negative and cannot use monotonic dominance for {race}: {value}",
            )
        return value, ()

    def build(
        self,
        objective_key: str,
        source_races: tuple[str, ...],
    ) -> ExtremeResourceRaceProjection:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme race projection objective: {objective_key!r}")

        races = tuple(str(race).strip() for race in tuple(source_races or ()) if str(race).strip())
        unresolved: list[str] = []
        if not races:
            unresolved.append("Canonical legal race universe is empty")

        reviewed: list[tuple[str, float]] = []
        for race in races:
            signature, race_unresolved = self._signature(race, key)
            unresolved.extend(race_unresolved)
            if signature is not None:
                reviewed.append((race, signature))

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        retained: tuple[str, ...] = ()
        signatures: tuple[float, ...] = ()
        if reviewed and not final_unresolved and len(reviewed) == len(races):
            best_value = max(value for _, value in reviewed)
            tied = tuple(
                race
                for race, value in reviewed
                if abs(value - best_value) <= 1e-9
            )
            witness = min(tied, key=lambda race: (race.casefold(), race))
            retained = (witness,)
            signatures = (float(best_value),)

        denominator_proven = bool(
            races
            and len(reviewed) == len(races)
            and retained
            and not final_unresolved
        )
        return ExtremeResourceRaceProjection(
            objective_key=key,
            source_race_count=len(races),
            races=retained,
            signatures=signatures,
            source_signatures=tuple(reviewed),
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourceRaceProjection",
    "ExtremeResourceRaceProjectionService",
]
