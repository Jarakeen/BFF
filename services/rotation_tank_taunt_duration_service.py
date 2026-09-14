from __future__ import annotations

"""Resolve source-backed taunt duration without inventing maintenance policy.

The service deliberately requires two independent facts to line up:

* canonical component utility evidence proves that the named source actually TAUNTs;
* canonical rotation-duration evidence collapses to one unambiguous positive duration.

A duration is promoted only when every positive canonical duration exposed for the
source agrees on the same value. This is intentionally conservative: a skill with
multiple distinct durations needs component-specific temporal binding before Tank
rotation code may use any one of them as taunt duration.
"""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Callable

from minmax.rotation_duration_evidence import resolve_rotation_duration_evidence
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import (
    SkillComponentUtilityEffectRepository,
)


@dataclass(frozen=True)
class RotationTankTauntDurationResolution:
    source_skill_name: str
    skill_rank_id: int | None
    ability_id: int | None
    duration_seconds: float | None
    taunt_component_numbers: tuple[int, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.duration_seconds is not None and not self.unresolved


class RotationTankTauntDurationService:
    """Resolve one canonical taunt duration while keeping refresh strategy separate."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | object | None = None,
        utility_repository: SkillComponentUtilityEffectRepository | object | None = None,
        duration_resolver: Callable[[str], object] | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.utility = utility_repository or SkillComponentUtilityEffectRepository(
            self.database_path
        )
        self.duration_resolver = duration_resolver or (
            lambda source_name: resolve_rotation_duration_evidence(
                source_name,
                database_path=self.database_path,
            )
        )

    def resolve(self, source_skill_name: str) -> RotationTankTauntDurationResolution:
        requested = str(source_skill_name or "").strip()
        if not requested:
            return RotationTankTauntDurationResolution(
                source_skill_name="",
                skill_rank_id=None,
                ability_id=None,
                duration_seconds=None,
                unresolved=("tank taunt duration requires source skill name",),
            )

        skill = self.coefficients.resolve_name(requested)
        rank = getattr(skill, "rank", None)
        if rank is None:
            messages = tuple(getattr(skill, "unresolved", ())) or (
                f"canonical skill identity unresolved for {requested}",
            )
            return RotationTankTauntDurationResolution(
                source_skill_name=requested,
                skill_rank_id=None,
                ability_id=None,
                duration_seconds=None,
                unresolved=messages,
            )

        taunt_components: list[int] = []
        evidence: list[str] = []
        for coefficient in tuple(getattr(rank, "coefficients", ())):
            number = int(getattr(coefficient, "coefficient_number"))
            for utility in self.utility.resolve(rank.skill_rank_id, number):
                if utility.effect_type is not SkillComponentUtilityEffectType.TAUNT:
                    continue
                taunt_components.append(number)
                evidence.append(
                    f"{rank.name} coefficient {number}: {utility.evidence}"
                )

        taunt_components = list(dict.fromkeys(taunt_components))
        evidence = list(dict.fromkeys(evidence))
        if not taunt_components:
            return RotationTankTauntDurationResolution(
                source_skill_name=rank.name,
                skill_rank_id=rank.skill_rank_id,
                ability_id=rank.ability_id,
                duration_seconds=None,
                unresolved=(
                    f"{rank.name} has no source-backed canonical taunt utility component",
                ),
            )

        duration_resolution = self.duration_resolver(rank.name)
        duration_rows = tuple(getattr(duration_resolution, "evidence", ()))
        positive = sorted(
            {
                float(getattr(item, "duration_seconds"))
                for item in duration_rows
                if getattr(item, "duration_seconds", None) is not None
                and math.isfinite(float(getattr(item, "duration_seconds")))
                and float(getattr(item, "duration_seconds")) > 0
            }
        )

        unresolved: list[str] = []
        if not positive:
            unresolved.extend(
                str(message)
                for message in tuple(getattr(duration_resolution, "unresolved", ()))
                if str(message).strip()
            )
            if not unresolved:
                unresolved.append(
                    f"no positive canonical duration evidence found for {rank.name}"
                )
            return RotationTankTauntDurationResolution(
                source_skill_name=rank.name,
                skill_rank_id=rank.skill_rank_id,
                ability_id=rank.ability_id,
                duration_seconds=None,
                taunt_component_numbers=tuple(taunt_components),
                evidence=tuple(evidence),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        if len(positive) > 1:
            rendered = ", ".join(f"{value:g}s" for value in positive)
            return RotationTankTauntDurationResolution(
                source_skill_name=rank.name,
                skill_rank_id=rank.skill_rank_id,
                ability_id=rank.ability_id,
                duration_seconds=None,
                taunt_component_numbers=tuple(taunt_components),
                evidence=tuple(evidence),
                unresolved=(
                    f"{rank.name}: multiple canonical durations require taunt-component temporal binding ({rendered})",
                ),
            )

        duration = positive[0]
        for item in duration_rows:
            value = getattr(item, "duration_seconds", None)
            if value is None or not math.isclose(float(value), duration, abs_tol=1e-9):
                continue
            effect_name = str(getattr(item, "effect_name", "duration")).strip() or "duration"
            source = str(getattr(item, "source", "canonical duration evidence")).strip()
            evidence.append(
                f"duration {duration:g}s from {source} ({effect_name})"
            )

        return RotationTankTauntDurationResolution(
            source_skill_name=rank.name,
            skill_rank_id=rank.skill_rank_id,
            ability_id=rank.ability_id,
            duration_seconds=duration,
            taunt_component_numbers=tuple(taunt_components),
            evidence=tuple(dict.fromkeys(evidence)),
        )


__all__ = [
    "RotationTankTauntDurationResolution",
    "RotationTankTauntDurationService",
]
