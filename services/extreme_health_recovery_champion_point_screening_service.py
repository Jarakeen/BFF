from __future__ import annotations

"""Objective-specific screening for unresolved Champion Point mechanics.

This layer answers only whether an unresolved Champion Point tooltip can directly
raise the Extreme ``health_recovery`` objective. It deliberately does not score
conditional mechanics or choose Champion Bar loadouts. Numeric projection and
slot legality belong to later proof layers.

The screen is description-driven and fail-closed for direct Health Recovery
mentions, including shared Health/Magicka/Stamina Recovery grammar. Mechanics
that merely alter duration, costs, Ultimate generation, or another recovery stat
are not direct Health Recovery contributors.
"""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.champion_point_static_repository import ChampionPointRecord


class ExtremeHealthRecoveryChampionPointScreeningStatus(str, Enum):
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeHealthRecoveryChampionPointScreening:
    record: ChampionPointRecord
    status: ExtremeHealthRecoveryChampionPointScreeningStatus
    evidence: tuple[str, ...] = ()

    @property
    def relevant(self) -> bool:
        return self.status is ExtremeHealthRecoveryChampionPointScreeningStatus.RELEVANT


class ExtremeHealthRecoveryChampionPointScreeningService:
    """Screen one CP tooltip for direct Health Recovery relevance."""

    _DIRECT_HEALTH_RECOVERY = re.compile(r"\bhealth\s+recovery\b", re.IGNORECASE)
    _SHARED_RECOVERY = re.compile(
        r"\bhealth\s*,\s*magicka\s*,?\s*(?:and\s+)?stamina\s+recovery\b",
        re.IGNORECASE,
    )

    @classmethod
    def screen(
        cls,
        record: ChampionPointRecord,
    ) -> ExtremeHealthRecoveryChampionPointScreening:
        text = " ".join(str(record.description or "").split())
        evidence: list[str] = []

        if cls._DIRECT_HEALTH_RECOVERY.search(text):
            evidence.append("direct Health Recovery reference")
        if cls._SHARED_RECOVERY.search(text):
            evidence.append("shared Health/Magicka/Stamina Recovery reference")

        if evidence:
            return ExtremeHealthRecoveryChampionPointScreening(
                record=record,
                status=ExtremeHealthRecoveryChampionPointScreeningStatus.RELEVANT,
                evidence=tuple(dict.fromkeys(evidence)),
            )

        return ExtremeHealthRecoveryChampionPointScreening(
            record=record,
            status=ExtremeHealthRecoveryChampionPointScreeningStatus.IRRELEVANT,
            evidence=("no direct Health Recovery mechanic in canonical tooltip",),
        )

    @classmethod
    def screen_many(
        cls,
        records: tuple[ChampionPointRecord, ...],
    ) -> tuple[ExtremeHealthRecoveryChampionPointScreening, ...]:
        return tuple(cls.screen(record) for record in records)


__all__ = [
    "ExtremeHealthRecoveryChampionPointScreening",
    "ExtremeHealthRecoveryChampionPointScreeningService",
    "ExtremeHealthRecoveryChampionPointScreeningStatus",
]
