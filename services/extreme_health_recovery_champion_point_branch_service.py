from __future__ import annotations

"""Classify and bound Health Recovery Champion Point mechanics.

This service operates only after objective-specific relevance screening. It provides
an individual-star numeric ceiling and runtime condition, but does not choose a
legal Champion Bar loadout or assert that multiple conditional maxima coexist.
"""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.champion_point_static_repository import ChampionPointRecord
from services.eso_character_progression_contract import ULTIMATE_RULES


_NUMBER = r"((?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))"


class ExtremeHealthRecoveryChampionPointBranchKind(str, Enum):
    PER_STAGE_FLAT = "per_stage_flat"
    CAPPED_DYNAMIC_FLAT = "capped_dynamic_flat"
    ULTIMATE_SCALED_FLAT = "ultimate_scaled_flat"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ExtremeHealthRecoveryChampionPointBranch:
    name: str
    kind: ExtremeHealthRecoveryChampionPointBranchKind
    flat_ceiling: float | None
    condition: str | None
    stages: int | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.flat_ceiling is not None and not self.unresolved


class ExtremeHealthRecoveryChampionPointBranchService:
    @staticmethod
    def _stages(record: ChampionPointRecord) -> int:
        points = max(0, int(record.max_points))
        thresholds = tuple(value for value in record.jump_points if int(value) > 0)
        if thresholds:
            return sum(1 for value in thresholds if points >= int(value))
        return points

    @classmethod
    def classify(
        cls,
        record: ChampionPointRecord,
    ) -> ExtremeHealthRecoveryChampionPointBranch:
        text = " ".join(str(record.description or "").split())

        strategic = re.search(
            rf"Gain\s+{_NUMBER}\s+Health Recovery for every\s+{_NUMBER}\s+Ultimate you have",
            text,
            flags=re.IGNORECASE,
        )
        if strategic:
            per_chunk = float(strategic.group(1))
            chunk_size = float(strategic.group(2))
            if chunk_size <= 0:
                return cls._unresolved(record, "Strategic Reserve Ultimate chunk must be positive")
            chunks = int(ULTIMATE_RULES.maximum_resource // chunk_size)
            return ExtremeHealthRecoveryChampionPointBranch(
                name=record.name,
                kind=ExtremeHealthRecoveryChampionPointBranchKind.ULTIMATE_SCALED_FLAT,
                flat_ceiling=per_chunk * chunks,
                condition=f"at {ULTIMATE_RULES.maximum_resource} stored Ultimate",
            )

        capped = re.search(
            rf"Health, Magicka, and Stamina Recovery equal to\s+{_NUMBER}% of your Max Magicka, up to a cap of\s+{_NUMBER}",
            text,
            flags=re.IGNORECASE,
        )
        if capped:
            return ExtremeHealthRecoveryChampionPointBranch(
                name=record.name,
                kind=ExtremeHealthRecoveryChampionPointBranchKind.CAPPED_DYNAMIC_FLAT,
                flat_ceiling=float(capped.group(2)),
                condition="overheal target; Max Magicka high enough to reach stated cap",
            )

        per_stage_patterns = (
            rf"Health and Magicka Recovery.*?{_NUMBER}\s+per stage",
            rf"Magicka and Health Recovery.*?by\s+{_NUMBER}\s+per stage",
            rf"{_NUMBER}\s+Health and Magicka Recovery per stage",
            rf"Health, Magicka, and Stamina Recovery by\s+{_NUMBER}\s+per stage",
        )
        for pattern in per_stage_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            stages = cls._stages(record)
            value = float(match.group(1)) * stages
            condition = cls._condition_from_text(text)
            return ExtremeHealthRecoveryChampionPointBranch(
                name=record.name,
                kind=ExtremeHealthRecoveryChampionPointBranchKind.PER_STAGE_FLAT,
                flat_ceiling=value,
                condition=condition,
                stages=stages,
            )

        return cls._unresolved(record, "unclassified Health Recovery Champion Point grammar")

    @staticmethod
    def _condition_from_text(text: str) -> str:
        lowered = text.casefold()
        if "crowd control immunity" in lowered:
            return "while under Crowd Control Immunity"
        if "while sprinting" in lowered:
            return "while Sprinting"
        if "negative effect" in lowered:
            return "while under a negative effect"
        return "runtime condition required"

    @staticmethod
    def _unresolved(
        record: ChampionPointRecord,
        problem: str,
    ) -> ExtremeHealthRecoveryChampionPointBranch:
        return ExtremeHealthRecoveryChampionPointBranch(
            name=record.name,
            kind=ExtremeHealthRecoveryChampionPointBranchKind.UNRESOLVED,
            flat_ceiling=None,
            condition=None,
            unresolved=(problem,),
        )


__all__ = [
    "ExtremeHealthRecoveryChampionPointBranch",
    "ExtremeHealthRecoveryChampionPointBranchKind",
    "ExtremeHealthRecoveryChampionPointBranchService",
]
