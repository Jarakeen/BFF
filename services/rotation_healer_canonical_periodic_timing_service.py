from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import sqlite3

from minmax.rotation_duration_evidence import resolve_rotation_duration_evidence
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
    extract_skill_component_runtime_timing,
)
from minmax.skill_component_text_evidence import extract_component_text_evidence
from services.rotation_healer_u50_periodic_cadence_repository import (
    RotationHealerU50PeriodicCadenceRepository,
)


@dataclass(frozen=True)
class RotationHealerCanonicalPeriodicTimingResolution:
    """Canonical timing evidence for one periodic healing coefficient.

    This resolution deliberately stops before inventing concrete tick timestamps.
    Coefficient text or narrowly reviewed U50 cadence evidence can prove cadence,
    and rotation-duration evidence can prove an active window. First-tick offset,
    exact expiry-boundary behavior, and recast/refresh semantics remain separate
    runtime facts unless independently verified.
    """

    source_name: str
    coefficient_number: int
    skill_rank_id: int | None
    ability_id: int | None
    component_fragment: str
    timing: SkillComponentRuntimeTiming | None
    duration_seconds: float | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def cadence_seconds(self) -> float | None:
        if self.timing is None:
            return None
        return self.timing.interval_seconds

    @property
    def timing_ready_for_runtime_binding(self) -> bool:
        return (
            self.timing is not None
            and self.cadence_seconds is not None
            and self.duration_seconds is not None
            and not self.unresolved
        )


class RotationHealerCanonicalPeriodicTimingService:
    """Resolve canonical/reviewed cadence plus Phase 13 duration evidence."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        reviewed_cadence_repository: RotationHealerU50PeriodicCadenceRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = SkillCoefficientRepository(self.database_path)
        self.reviewed_cadence = (
            reviewed_cadence_repository
            or RotationHealerU50PeriodicCadenceRepository()
        )

    def resolve(
        self,
        *,
        source_name: str,
        coefficient_number: int,
    ) -> RotationHealerCanonicalPeriodicTimingResolution:
        name = str(source_name or "").strip()
        number = int(coefficient_number)
        unresolved: list[str] = []
        evidence: list[str] = []

        if not name:
            return RotationHealerCanonicalPeriodicTimingResolution(
                source_name="",
                coefficient_number=number,
                skill_rank_id=None,
                ability_id=None,
                component_fragment="",
                timing=None,
                duration_seconds=None,
                unresolved=("periodic healing source name is required",),
            )

        skill = self.coefficients.resolve_name(name)
        if skill.rank is None:
            messages = skill.unresolved or (f"canonical skill identity unresolved for {name}",)
            return RotationHealerCanonicalPeriodicTimingResolution(
                source_name=name,
                coefficient_number=number,
                skill_rank_id=None,
                ability_id=None,
                component_fragment="",
                timing=None,
                duration_seconds=None,
                unresolved=tuple(messages),
            )

        rank = skill.rank
        description = self._coef_description(rank.ability_id)
        if not description:
            unresolved.append(
                f"{rank.name}: canonical coef_description is unavailable for periodic timing"
            )
            component_fragment = ""
            timing = None
        else:
            component = extract_component_text_evidence(description, number)
            component_fragment = component.fragment
            if not component_fragment:
                unresolved.append(
                    f"{rank.name} coefficient {number}: coefficient-owned text fragment is unavailable"
                )
                timing = None
            elif component.effect_kind != "heal" or component.is_dot is not True:
                unresolved.append(
                    f"{rank.name} coefficient {number}: canonical text does not prove periodic healing identity"
                )
                timing = None
            else:
                timing = extract_skill_component_runtime_timing(component_fragment)
                evidence.extend(component.evidence)
                if timing is None:
                    reviewed = self.reviewed_cadence.get(
                        source_name=rank.name,
                        coefficient_number=number,
                    )
                    if reviewed is None:
                        unresolved.append(
                            f"{rank.name} coefficient {number}: canonical periodic cadence is unresolved"
                        )
                    else:
                        timing = reviewed.timing
                        evidence.append(
                            f"reviewed U50 cadence: {timing.evidence} ({timing.bound_kind.value})"
                        )
                        evidence.extend(reviewed.provenance)
                else:
                    evidence.append(
                        f"runtime cadence: {timing.evidence} ({timing.bound_kind.value})"
                    )

        duration_seconds = self._resolve_duration_seconds(
            rank.name,
            timing=timing,
            evidence=evidence,
            unresolved=unresolved,
        )

        if timing is not None and timing.interval_seconds is None:
            unresolved.append(
                f"{rank.name} coefficient {number}: exact within-window tick interval remains unresolved"
            )

        return RotationHealerCanonicalPeriodicTimingResolution(
            source_name=rank.name,
            coefficient_number=number,
            skill_rank_id=rank.skill_rank_id,
            ability_id=rank.ability_id,
            component_fragment=component_fragment,
            timing=timing,
            duration_seconds=duration_seconds,
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _coef_description(self, ability_id: int) -> str:
        if not self.database_path.exists():
            return ""
        try:
            with sqlite3.connect(self.database_path) as db:
                columns = {
                    str(row[1])
                    for row in db.execute("PRAGMA table_info(ability)").fetchall()
                }
                if not {"ability_id", "coef_description"}.issubset(columns):
                    return ""
                row = db.execute(
                    "SELECT coef_description FROM ability WHERE ability_id = ?",
                    (int(ability_id),),
                ).fetchone()
        except sqlite3.Error:
            return ""
        if row is None or row[0] is None:
            return ""
        return " ".join(str(row[0]).split())

    def _resolve_duration_seconds(
        self,
        source_name: str,
        *,
        timing: SkillComponentRuntimeTiming | None,
        evidence: list[str],
        unresolved: list[str],
    ) -> float | None:
        if (
            timing is not None
            and timing.bound_kind is RuntimeCadenceBoundKind.FIXED_COUNT_DURATION
            and timing.duration_seconds is not None
        ):
            duration = float(timing.duration_seconds)
            evidence.append(
                f"component runtime wording proves {duration:g}s periodic duration"
            )
            return duration

        duration_resolution = resolve_rotation_duration_evidence(
            source_name,
            database_path=self.database_path,
        )
        if duration_resolution.unresolved:
            unresolved.extend(duration_resolution.unresolved)

        positive = sorted(
            {
                float(item.duration_seconds)
                for item in duration_resolution.evidence
                if math.isfinite(float(item.duration_seconds))
                and float(item.duration_seconds) > 0
            }
        )
        if not positive:
            return None
        if len(positive) > 1:
            rendered = ", ".join(f"{value:g}s" for value in positive)
            unresolved.append(
                f"{source_name}: multiple canonical durations require component-specific binding ({rendered})"
            )
            return None

        duration = positive[0]
        for item in duration_resolution.evidence:
            if math.isclose(float(item.duration_seconds), duration, abs_tol=1e-9):
                evidence.append(
                    f"duration {duration:g}s from {item.source} ({item.effect_name})"
                )
        return duration
