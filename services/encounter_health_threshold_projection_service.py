from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.fight_damage_trajectory import (
    FightDamageTrajectoryProjection,
    RaidDamageSegment,
    project_health_threshold_times,
)
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide


_PERCENT = re.compile(r"^\s*(100|[1-9]?\d(?:\.\d+)?)\s*%\s*$")
_HEALTH = re.compile(r"^\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\s*\(([^()]*)\))?\s*$")


@dataclass(frozen=True)
class EncounterThresholdClockPoint:
    fact_key: str
    label: str
    threshold_fraction: float
    time_seconds: float | None
    resolved: bool
    reason: str


@dataclass(frozen=True)
class EncounterHealthThresholdProjection:
    encounter_id: str
    difficulty: str
    maximum_health: int | None
    trajectory: FightDamageTrajectoryProjection | None
    points: tuple[EncounterThresholdClockPoint, ...]
    unresolved: tuple[str, ...]


def _parse_health(raw: str) -> int | None:
    match = _HEALTH.fullmatch(str(raw or ""))
    if match is None:
        return None
    return int(match.group(1).replace(",", ""))


def _thresholds(fact: BossGuideTimelineFact) -> tuple[float, ...]:
    payload = fact.payload
    raw_values = payload.get("thresholds")
    values = raw_values if isinstance(raw_values, (list, tuple)) else (
        payload.get("threshold") or payload.get("starts_at"),
    )
    resolved = []
    for raw in values:
        if raw is None:
            continue
        match = _PERCENT.fullmatch(str(raw))
        if match is None:
            continue
        percent = float(match.group(1))
        if percent <= 0 or percent >= 100:
            continue
        resolved.append(percent / 100.0)
    return tuple(resolved)


def _label(fact: BossGuideTimelineFact) -> str:
    return str(
        fact.payload.get("label")
        or fact.payload.get("name")
        or fact.fact_key.replace("_", " ").strip().title()
        or "Encounter Threshold"
    ).strip()


class EncounterHealthThresholdProjectionService:
    """Project reviewed health-threshold facts into clock points from explicit raid DPS.

    Encounter facts own the health thresholds. Boss-guide persistence owns source
    health text. Raid damage segments are caller supplied or come from another
    verified projection layer. This service never derives raid DPS from single-event
    build potency or candidate-ranking metrics.
    """

    def project(
        self,
        *,
        guide: EncounterBossGuide,
        difficulty: str,
        damage_segments: tuple[RaidDamageSegment, ...],
    ) -> EncounterHealthThresholdProjection:
        difficulty_key = str(difficulty or "").strip().casefold()
        if difficulty_key not in {"normal", "veteran", "hardmode"}:
            raise ValueError("difficulty must be normal, veteran, or hardmode")

        raw_health = dict(guide.health).get(difficulty_key, "")
        maximum_health = _parse_health(raw_health)
        unresolved: list[str] = []
        if maximum_health is None:
            unresolved.append(
                f"{difficulty_key}: canonical encounter health is missing or not unambiguously numeric"
            )
            return EncounterHealthThresholdProjection(
                encounter_id=guide.encounter_id,
                difficulty=difficulty_key,
                maximum_health=None,
                trajectory=None,
                points=(),
                unresolved=tuple(unresolved),
            )

        threshold_rows: list[tuple[BossGuideTimelineFact, float]] = []
        for fact in guide.timeline_facts:
            if not str(fact.review_status or "").casefold().startswith("reviewed"):
                continue
            if fact.evidence_count <= 0:
                continue
            fractions = _thresholds(fact)
            for fraction in fractions:
                threshold_rows.append((fact, fraction))

        if not threshold_rows:
            unresolved.append("no reviewed canonical health-threshold facts are available")
            return EncounterHealthThresholdProjection(
                encounter_id=guide.encounter_id,
                difficulty=difficulty_key,
                maximum_health=maximum_health,
                trajectory=None,
                points=(),
                unresolved=tuple(unresolved),
            )

        trajectory = project_health_threshold_times(
            maximum_health=maximum_health,
            thresholds=tuple(fraction for _, fraction in threshold_rows),
            segments=tuple(damage_segments),
        )

        points = []
        for (fact, fraction), projected in zip(threshold_rows, trajectory.thresholds):
            points.append(
                EncounterThresholdClockPoint(
                    fact_key=fact.fact_key,
                    label=_label(fact),
                    threshold_fraction=fraction,
                    time_seconds=projected.time_seconds,
                    resolved=projected.resolved,
                    reason=projected.reason,
                )
            )
            if not projected.resolved:
                unresolved.append(
                    f"{fact.fact_key} at {fraction * 100:g}%: {projected.reason}"
                )

        return EncounterHealthThresholdProjection(
            encounter_id=guide.encounter_id,
            difficulty=difficulty_key,
            maximum_health=maximum_health,
            trajectory=trajectory,
            points=tuple(points),
            unresolved=tuple(unresolved),
        )
