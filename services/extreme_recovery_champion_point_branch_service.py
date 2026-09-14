from __future__ import annotations

"""Classify and bound Recovery Champion Point mechanics across all three Recovery stats."""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.champion_point_static_repository import ChampionPointRecord
from services.eso_character_progression_contract import ULTIMATE_RULES

_NUMBER = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
_SUPPORTED = {"health_recovery", "magicka_recovery", "stamina_recovery"}
_RESOURCE = {
    "health_recovery": "health",
    "magicka_recovery": "magicka",
    "stamina_recovery": "stamina",
}
_RESOURCE_LIST = r"(?:health|magicka|stamina)(?:(?:\s*,\s*|\s+and\s+|\s*,\s*and\s+)(?:health|magicka|stamina)){0,2}"
_REFERENCE_ONLY_TEMPLATE = r"for every\s+\d+(?:\.\d+)?\s+{resource}\s+recovery\s+you have"


class ExtremeRecoveryChampionPointBranchKind(str, Enum):
    PER_STAGE_FLAT = "per_stage_flat"
    CAPPED_DYNAMIC_FLAT = "capped_dynamic_flat"
    ULTIMATE_SCALED_FLAT = "ultimate_scaled_flat"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ExtremeRecoveryChampionPointBranch:
    name: str
    objective_key: str
    kind: ExtremeRecoveryChampionPointBranchKind
    flat_ceiling: float | None
    condition: str | None
    stages: int | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.flat_ceiling is not None and not self.unresolved


class ExtremeRecoveryChampionPointBranchService:
    @staticmethod
    def _stages(record: ChampionPointRecord) -> int:
        points = max(0, int(record.max_points))
        thresholds = tuple(value for value in record.jump_points if int(value) > 0)
        if thresholds:
            return sum(1 for value in thresholds if points >= int(value))
        return points

    @classmethod
    def mentions_objective_recovery(cls, text: str, objective_key: str) -> bool:
        objective = str(objective_key or "").strip().casefold()
        if objective not in _SUPPORTED:
            raise KeyError(f"unsupported Recovery Champion Point objective: {objective_key!r}")
        resource = _RESOURCE[objective]
        lowered = " ".join(str(text or "").casefold().split())

        # Recovery can appear only as an input/threshold to another effect. Remove
        # those clauses before deciding whether the star actually raises Recovery.
        # Hope Infusion is the canonical example: Minor Heroism scales with the
        # player's Magicka Recovery but does not itself grant Magicka Recovery.
        lowered = re.sub(
            _REFERENCE_ONLY_TEMPLATE.format(resource=re.escape(resource)),
            "",
            lowered,
            flags=re.IGNORECASE,
        )

        if f"{resource} recovery" in lowered:
            return True
        if resource not in lowered or "recovery" not in lowered:
            return False
        resources = {name for name in ("health", "magicka", "stamina") if name in lowered}
        return resource in resources and len(resources) >= 2

    @classmethod
    def classify(
        cls,
        record: ChampionPointRecord,
        objective_key: str,
    ) -> ExtremeRecoveryChampionPointBranch:
        objective = str(objective_key or "").strip().casefold()
        if objective not in _SUPPORTED:
            raise KeyError(f"unsupported Recovery Champion Point objective: {objective_key!r}")
        text = " ".join(str(record.description or "").split())

        if objective == "health_recovery":
            strategic = re.search(
                rf"Gain\s+({_NUMBER})\s+Health Recovery for every\s+({_NUMBER})\s+Ultimate you have",
                text,
                flags=re.IGNORECASE,
            )
            if strategic:
                per_chunk = float(strategic.group(1))
                chunk_size = float(strategic.group(2))
                if chunk_size <= 0:
                    return cls._unresolved(record, objective, "Strategic Reserve Ultimate chunk must be positive")
                chunks = int(ULTIMATE_RULES.maximum_resource // chunk_size)
                return ExtremeRecoveryChampionPointBranch(
                    name=record.name,
                    objective_key=objective,
                    kind=ExtremeRecoveryChampionPointBranchKind.ULTIMATE_SCALED_FLAT,
                    flat_ceiling=per_chunk * chunks,
                    condition=f"at {ULTIMATE_RULES.maximum_resource} stored Ultimate",
                )

        capped = re.search(
            rf"Health, Magicka, and Stamina Recovery equal to\s+({_NUMBER})% of your Max Magicka, up to a cap of\s+({_NUMBER})",
            text,
            flags=re.IGNORECASE,
        )
        if capped and cls.mentions_objective_recovery(text, objective):
            return ExtremeRecoveryChampionPointBranch(
                name=record.name,
                objective_key=objective,
                kind=ExtremeRecoveryChampionPointBranchKind.CAPPED_DYNAMIC_FLAT,
                flat_ceiling=float(capped.group(2)),
                condition="overheal target; Max Magicka high enough to reach stated cap",
            )

        if cls.mentions_objective_recovery(text, objective) and "per stage" in text.casefold():
            values: list[float] = []

            # "Grants 18 Health, Magicka, and Stamina Recovery per stage."
            # "While Sprinting you gain 100 Health and Magicka Recovery per stage."
            values.extend(
                float(value)
                for value in re.findall(
                    rf"({_NUMBER})\s+{_RESOURCE_LIST}\s+recovery\s+per stage",
                    text,
                    flags=re.IGNORECASE,
                )
            )

            # "Increases Magicka and Health Recovery while ... by 40 per stage."
            # "Increases your Health, Magicka, and Stamina Recovery by 30 per stage while ..."
            values.extend(
                float(value)
                for value in re.findall(
                    rf"{_RESOURCE_LIST}\s+recovery\b[^.]*?\bby\s+({_NUMBER})\s+per stage",
                    text,
                    flags=re.IGNORECASE,
                )
            )

            if values:
                stages = cls._stages(record)
                return ExtremeRecoveryChampionPointBranch(
                    name=record.name,
                    objective_key=objective,
                    kind=ExtremeRecoveryChampionPointBranchKind.PER_STAGE_FLAT,
                    flat_ceiling=max(values) * stages,
                    condition=cls._condition_from_text(text),
                    stages=stages,
                )

        return cls._unresolved(
            record,
            objective,
            f"unclassified {objective.replace('_', ' ')} Champion Point grammar",
        )

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
        objective_key: str,
        problem: str,
    ) -> ExtremeRecoveryChampionPointBranch:
        return ExtremeRecoveryChampionPointBranch(
            name=record.name,
            objective_key=objective_key,
            kind=ExtremeRecoveryChampionPointBranchKind.UNRESOLVED,
            flat_ceiling=None,
            condition=None,
            unresolved=(problem,),
        )


__all__ = [
    "ExtremeRecoveryChampionPointBranch",
    "ExtremeRecoveryChampionPointBranchKind",
    "ExtremeRecoveryChampionPointBranchService",
]
