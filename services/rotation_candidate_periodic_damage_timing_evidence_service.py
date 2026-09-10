from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from minmax.rotation_duration_evidence import resolve_rotation_duration_evidence
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
    extract_skill_component_runtime_timing,
)
from minmax.skill_component_text_evidence import extract_component_text_evidence


@dataclass(frozen=True)
class RotationPeriodicDamageTimingEntry:
    """Canonical cadence/duration evidence for one periodic damage component.

    This record deliberately stops before concrete tick scheduling. ESO does not
    guarantee one universal first-tick offset or one universal refresh boundary
    rule, so those runtime facts must be supplied by reviewed evidence before the
    DD output layer may turn this timing into damage events.
    """

    source_name: str
    coefficient_number: int
    skill_rank_id: int
    ability_id: int
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

    @property
    def runtime_binding_gaps(self) -> tuple[str, ...]:
        """Facts still required before exact tick timestamps are legal."""

        if not self.timing_ready_for_runtime_binding:
            return self.unresolved
        return (
            "first actual periodic-damage tick offset requires reviewed runtime evidence",
            "periodic-damage recast/refresh boundary semantics require reviewed runtime evidence",
        )


@dataclass(frozen=True)
class RotationPeriodicDamageTimingReport:
    action: RotationAction
    entries: tuple[RotationPeriodicDamageTimingEntry, ...]
    unresolved: tuple[str, ...] = ()


class RotationCandidatePeriodicDamageTimingEvidenceService:
    """Resolve periodic-damage cadence and duration for one scheduled skill.

    This is a composition helper over existing shared mechanics. Canonical skill
    identity remains owned by ``SkillCoefficientRepository``; component identity
    by ``SkillComponentRepository``; coefficient-local cadence by
    ``extract_skill_component_runtime_timing``; and duration by the existing
    rotation-duration evidence resolver. The service does not invent first-tick
    timing, refresh semantics, or concrete tick events.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        component_repository: SkillComponentRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.components = component_repository or SkillComponentRepository(
            self.database_path
        )

    def inspect_action(self, action: RotationAction) -> RotationPeriodicDamageTimingReport:
        if action.kind is not RotationActionKind.SKILL:
            return RotationPeriodicDamageTimingReport(
                action=action,
                entries=(),
                unresolved=(
                    f"{action.kind.value} is not a scheduled skill action for periodic-damage timing",
                ),
            )
        if not str(action.name or "").strip():
            return RotationPeriodicDamageTimingReport(
                action=action,
                entries=(),
                unresolved=("scheduled skill action has no canonical skill identity",),
            )

        resolution = self.coefficients.resolve_entity_id(str(action.name))
        if resolution.rank is None:
            return RotationPeriodicDamageTimingReport(
                action=action,
                entries=(),
                unresolved=resolution.unresolved
                or (f"canonical skill identity unresolved for {action.name}",),
            )

        rank = resolution.rank
        description = self._coef_description(rank.ability_id)
        classifications = self.components.get_for_skill_rank(rank.skill_rank_id)
        entries: list[RotationPeriodicDamageTimingEntry] = []
        report_unresolved: list[str] = []

        for component in classifications:
            if component.effect_kind is not SkillEffectKind.DAMAGE or component.is_dot is not True:
                continue

            unresolved: list[str] = []
            evidence: list[str] = []
            fragment = ""
            timing: SkillComponentRuntimeTiming | None = None

            if not description:
                unresolved.append(
                    f"{rank.name}: canonical coef_description is unavailable for periodic damage timing"
                )
            else:
                text = extract_component_text_evidence(
                    description,
                    component.coefficient_number,
                )
                fragment = text.fragment
                evidence.extend(text.evidence)
                if not fragment:
                    unresolved.append(
                        f"{rank.name} coefficient {component.coefficient_number}: coefficient-owned text fragment is unavailable"
                    )
                else:
                    timing = extract_skill_component_runtime_timing(fragment)
                    if timing is None:
                        unresolved.append(
                            f"{rank.name} coefficient {component.coefficient_number}: canonical periodic cadence is unresolved"
                        )
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
                    f"{rank.name} coefficient {component.coefficient_number}: exact within-window tick interval remains unresolved"
                )

            entry = RotationPeriodicDamageTimingEntry(
                source_name=rank.name,
                coefficient_number=component.coefficient_number,
                skill_rank_id=rank.skill_rank_id,
                ability_id=rank.ability_id,
                component_fragment=fragment,
                timing=timing,
                duration_seconds=duration_seconds,
                evidence=tuple(dict.fromkeys(evidence)),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )
            entries.append(entry)
            report_unresolved.extend(entry.unresolved)

        return RotationPeriodicDamageTimingReport(
            action=action,
            entries=tuple(entries),
            unresolved=tuple(dict.fromkeys(report_unresolved)),
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


__all__ = [
    "RotationCandidatePeriodicDamageTimingEvidenceService",
    "RotationPeriodicDamageTimingEntry",
    "RotationPeriodicDamageTimingReport",
]
