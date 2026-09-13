from __future__ import annotations

"""Proof-classify racial parser boundaries for Extreme max-resource objectives.

The canonical racial passive repository intentionally emits boundary messages for
passives that are outside its combat-stat mapping. Some of those boundaries are
nevertheless provably irrelevant to Max Health/Magicka/Stamina because the
repository itself classifies the passive as non-combat, current-resource sustain,
consumable-duration only, environmental mitigation only, or because the boundary
explicitly describes an ability cost modifier rather than a maximum-resource
modifier.

This service does not suppress arbitrary parser warnings. It accepts a boundary only
when the message belongs to one of the canonical repository's objective-neutral
classifications, or to the repository's explicit ability-cost boundary contract.
Everything else remains unresolved.
"""

from dataclasses import dataclass
from pathlib import Path
import re

from minmax.racial_passive_stat_repository import RacialPassiveStatRepository


_SUPPORTED_OBJECTIVES = frozenset({"max_health", "max_magicka", "max_stamina"})

_NONCOMBAT = re.compile(
    r"^Non-combat racial passive outside combat capability audit:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_RESOURCE_SUSTAIN = re.compile(
    r"^Racial passive restores current resources or alters mitigation without changing maximum resources:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_CONSUMABLE_DURATION = re.compile(
    r"^Racial passive changes consumable duration or skill-line experience without changing maximum resources:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_ENVIRONMENTAL_MITIGATION = re.compile(
    r"^Racial environmental-damage mitigation requires mitigation model:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_ABILITY_COST = re.compile(
    r"^Racial ability-cost reduction requires cost-stat model:\s*(.+?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtremeResourceRacialBoundaryRelevance:
    objective_key: str
    reviewed: tuple[str, ...]
    proven_irrelevant: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def denominator_proven(self) -> bool:
        return bool(self.reviewed) and len(self.reviewed) == (
            len(self.proven_irrelevant) + len(self.unresolved)
        )

    @property
    def objective_irrelevance_proven(self) -> bool:
        return self.denominator_proven and not self.unresolved


class ExtremeResourceRacialBoundaryRelevanceService:
    """Prove canonical racial boundary messages irrelevant to a max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: RacialPassiveStatRepository | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no racial repository is supplied")
        self.repository = repository or RacialPassiveStatRepository(database_path)  # type: ignore[arg-type]

    @staticmethod
    def _canonical_names(values) -> frozenset[str]:
        return frozenset(
            str(value or "").strip().casefold()
            for value in values
            if str(value or "").strip()
        )

    def _proven_irrelevant(self, message: str) -> bool:
        match = _NONCOMBAT.match(message)
        if match:
            return match.group(1).strip().casefold() in self._canonical_names(
                self.repository.NONCOMBAT_PASSIVE_NAMES
            )

        match = _RESOURCE_SUSTAIN.match(message)
        if match:
            return match.group(1).strip().casefold() in self._canonical_names(
                self.repository.RESOURCE_SUSTAIN_PASSIVE_NAMES
            )

        match = _CONSUMABLE_DURATION.match(message)
        if match:
            return match.group(1).strip().casefold() in self._canonical_names(
                self.repository.CONSUMABLE_DURATION_PASSIVE_NAMES
            )

        match = _ENVIRONMENTAL_MITIGATION.match(message)
        if match:
            return match.group(1).strip().casefold() in self._canonical_names(
                self.repository.MITIGATION_PASSIVE_NAMES
            )

        # This boundary is emitted only by RacialPassiveStatRepository when the
        # canonical tooltip explicitly reduces Magicka/Stamina/general ability
        # cost. Cost changes can affect sustain, but cannot change a maximum
        # Health/Magicka/Stamina snapshot, so they are objective-neutral here.
        if _ABILITY_COST.match(message):
            return True

        return False

    def build(
        self,
        objective_key: str,
        boundaries: tuple[str, ...],
    ) -> ExtremeResourceRacialBoundaryRelevance:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme racial boundary objective: {objective_key!r}")

        reviewed = tuple(
            dict.fromkeys(
                str(item or "").strip()
                for item in boundaries
                if str(item or "").strip()
            )
        )
        irrelevant: list[str] = []
        unresolved: list[str] = []
        for message in reviewed:
            if self._proven_irrelevant(message):
                irrelevant.append(message)
            else:
                unresolved.append(message)

        return ExtremeResourceRacialBoundaryRelevance(
            objective_key=key,
            reviewed=reviewed,
            proven_irrelevant=tuple(irrelevant),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeResourceRacialBoundaryRelevance",
    "ExtremeResourceRacialBoundaryRelevanceService",
]
