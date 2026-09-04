from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3

from .skill_coefficient_repository import SkillCoefficientRepository
from .skill_effect_repository import DEFAULT_DATABASE, SkillEffectRepository


@dataclass(frozen=True)
class RotationDurationEvidence:
    """One canonical duration-bearing effect exposed to the rotation layer."""

    effect_name: str
    duration_seconds: float
    source: str
    condition: str | None = None


@dataclass(frozen=True)
class RotationDurationResolution:
    """Duration evidence for one named skill without inferring recast policy."""

    skill_name: str
    ability_id: int | None
    evidence: tuple[RotationDurationEvidence, ...] = ()
    unresolved: tuple[str, ...] = ()


def _ability_duration_seconds(
    database_path: str | Path,
    ability_id: int,
) -> float | None:
    """Read imported ``ability.duration`` as canonical fallback evidence.

    The ability table stores duration in ESO API milliseconds. This fallback is
    used only when no linked/supplemental EffectVariant exposes a positive
    duration, so it recovers canonical timing without manufacturing an effect
    identity or duplicating richer effect evidence.
    """

    path = Path(database_path)
    if not path.exists():
        return None

    try:
        with sqlite3.connect(path) as db:
            columns = {
                str(row[1])
                for row in db.execute("PRAGMA table_info(ability)").fetchall()
            }
            if not {"ability_id", "duration"}.issubset(columns):
                return None
            row = db.execute(
                "SELECT duration FROM ability WHERE ability_id = ?",
                (int(ability_id),),
            ).fetchone()
    except sqlite3.Error:
        return None

    if row is None or row[0] is None:
        return None
    try:
        milliseconds = float(row[0])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(milliseconds) or milliseconds <= 0:
        return None
    return milliseconds / 1000.0


def resolve_rotation_duration_evidence(
    skill_name: str,
    *,
    database_path: str | Path = DEFAULT_DATABASE,
) -> RotationDurationResolution:
    """Resolve canonical duration-bearing effects for one named skill.

    This adapter deliberately stops at evidence. A skill can expose multiple
    durations, and Phase 13 must not silently turn any one of them into a recast
    interval without an explicit scheduling rule.

    SkillCoefficientRepository is currently reused for its established named
    skill/rank identity crosswalk. Once identity succeeds, missing coefficient
    rows are irrelevant to duration resolution and therefore are not propagated
    as duration failures.
    """

    requested = str(skill_name or "").strip()
    if not requested:
        return RotationDurationResolution(
            skill_name="",
            ability_id=None,
            unresolved=("skill name is required for duration evidence",),
        )

    skill_repository = SkillCoefficientRepository(database_path)
    skill_resolution = skill_repository.resolve_name(requested)
    if skill_resolution.rank is None:
        return RotationDurationResolution(
            skill_name=requested,
            ability_id=None,
            unresolved=skill_resolution.unresolved
            or (f"canonical skill identity unresolved for {requested}",),
        )

    rank = skill_resolution.rank
    effect_repository = SkillEffectRepository(database_path)
    effects = effect_repository.resolve(rank.ability_id)

    evidence: list[RotationDurationEvidence] = []
    for effect in effects:
        if effect.duration is None:
            continue
        duration = float(effect.duration)
        if not math.isfinite(duration) or duration <= 0:
            continue
        evidence.append(
            RotationDurationEvidence(
                effect_name=str(effect.name),
                duration_seconds=duration,
                source=str(effect.source),
                condition=(
                    str(effect.condition).strip()
                    if effect.condition is not None and str(effect.condition).strip()
                    else None
                ),
            )
        )

    if not evidence:
        ability_duration = _ability_duration_seconds(database_path, rank.ability_id)
        if ability_duration is not None:
            evidence.append(
                RotationDurationEvidence(
                    effect_name="ability_duration",
                    duration_seconds=ability_duration,
                    source=f"{rank.name} ability.duration",
                )
            )

    ordered = tuple(
        sorted(
            evidence,
            key=lambda value: (
                value.duration_seconds,
                value.effect_name.casefold(),
                value.source.casefold(),
                value.condition or "",
            ),
        )
    )

    unresolved: tuple[str, ...] = ()
    if not ordered:
        unresolved = (
            f"no positive canonical duration evidence found for {rank.name}",
        )

    return RotationDurationResolution(
        skill_name=rank.name,
        ability_id=rank.ability_id,
        evidence=ordered,
        unresolved=unresolved,
    )
