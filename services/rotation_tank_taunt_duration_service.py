from __future__ import annotations

"""Resolve source-backed taunt duration without inventing maintenance policy.

The strongest path binds duration directly to the same coefficient-owned canonical
text that proves TAUNT identity. Generic rotation-duration evidence remains a
fallback only when the taunt component text does not itself expose a duration.

A duration is promoted only when the source-backed taunt evidence and temporal
evidence are unambiguous. Refresh cadence, maintenance policy, overtaunt/immunity,
and safety margins remain separate concerns.
"""

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Callable

from minmax.rotation_duration_evidence import resolve_rotation_duration_evidence
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import (
    SkillComponentUtilityEffectRepository,
)


_TAUNT_DURATION_RE = re.compile(
    r"\btaunt(?:s|ed|ing)?\b[^.;]{0,120}?\bfor\s+"
    r"(?P<seconds>\d+(?:\.\d+)?)\s+seconds?\b",
    re.IGNORECASE,
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
        component_durations: list[tuple[int, float, str]] = []
        resolve_component_text = getattr(self.utility, "resolve_component_text", None)

        for coefficient in tuple(getattr(rank, "coefficients", ())):
            number = int(getattr(coefficient, "coefficient_number"))
            utilities = tuple(self.utility.resolve(rank.skill_rank_id, number))
            if not any(
                utility.effect_type is SkillComponentUtilityEffectType.TAUNT
                for utility in utilities
            ):
                continue

            taunt_components.append(number)
            for utility in utilities:
                if utility.effect_type is SkillComponentUtilityEffectType.TAUNT:
                    evidence.append(
                        f"{rank.name} coefficient {number}: {utility.evidence}"
                    )

            if callable(resolve_component_text):
                component_text = str(
                    resolve_component_text(rank.skill_rank_id, number) or ""
                ).strip()
                match = _TAUNT_DURATION_RE.search(component_text)
                if match is not None:
                    duration = float(match.group("seconds"))
                    if math.isfinite(duration) and duration > 0:
                        component_durations.append(
                            (number, duration, match.group(0).strip())
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

        if component_durations:
            distinct_component_durations = sorted(
                {duration for _, duration, _ in component_durations}
            )
            if len(distinct_component_durations) > 1:
                rendered = ", ".join(
                    f"{value:g}s" for value in distinct_component_durations
                )
                return RotationTankTauntDurationResolution(
                    source_skill_name=rank.name,
                    skill_rank_id=rank.skill_rank_id,
                    ability_id=rank.ability_id,
                    duration_seconds=None,
                    taunt_component_numbers=tuple(taunt_components),
                    evidence=tuple(evidence),
                    unresolved=(
                        f"{rank.name}: conflicting coefficient-owned taunt durations ({rendered})",
                    ),
                )

            duration = distinct_component_durations[0]
            for number, value, text in component_durations:
                if math.isclose(value, duration, abs_tol=1e-9):
                    evidence.append(
                        f"{rank.name} coefficient {number} taunt duration {duration:g}s: {text}"
                    )
            return RotationTankTauntDurationResolution(
                source_skill_name=rank.name,
                skill_rank_id=rank.skill_rank_id,
                ability_id=rank.ability_id,
                duration_seconds=duration,
                taunt_component_numbers=tuple(taunt_components),
                evidence=tuple(dict.fromkeys(evidence)),
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
