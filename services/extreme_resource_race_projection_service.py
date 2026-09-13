from __future__ import annotations

"""Proof-reduce legal races for Extreme max-resource scoring.

The complete legal race universe remains the denominator.  For a scalar maximum
resource objective, one legal race may represent another only when the canonical
racial progression and tooltip resolver completely account for both races and the
requested max-resource contribution is exactly equal.

Race identity is never erased on unresolved canonical evidence.  Non-target racial
stats remain outside this scalar projection; they continue to be owned by the
canonical racial passive resolver and passive coverage audits.
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
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.denominator_proven
            and self.source_race_count > 0
            and self.races
            and len(self.races) == len(self.signatures)
            and not self.unresolved
        )

    @property
    def scope(self) -> tuple[str, ...]:
        if not self.projection_complete:
            return ()
        return (
            "legal races proof-reduced by complete canonical racial-passive target-resource "
            f"signature; {self.source_race_count} legal races -> {len(self.races)} exact witnesses",
        )


class ExtremeResourceRaceProjectionService:
    """Collapse legal races by exact canonical target-resource contribution."""

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

        witnesses: dict[float, str] = {}
        for race in races:
            signature, race_unresolved = self._signature(race, key)
            unresolved.extend(race_unresolved)
            if signature is None:
                continue
            current = witnesses.get(signature)
            if current is None or race.casefold() < current.casefold():
                witnesses[signature] = race

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        signatures = tuple(sorted(witnesses))
        retained = tuple(witnesses[signature] for signature in signatures)
        denominator_proven = bool(
            races
            and len(witnesses) > 0
            and not final_unresolved
        )
        return ExtremeResourceRaceProjection(
            objective_key=key,
            source_race_count=len(races),
            races=retained,
            signatures=signatures,
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourceRaceProjection",
    "ExtremeResourceRaceProjectionService",
]
