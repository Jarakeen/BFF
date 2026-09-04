from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from models.build_model import PlayerBuild

from .rotation_duration_evidence import (
    RotationDurationResolution,
    resolve_rotation_duration_evidence,
)
from .rotation_plan import RotationActionKind
from .skill_effect_repository import DEFAULT_DATABASE


@dataclass(frozen=True)
class SavedBuildSkillTimingEvidence:
    """Canonical duration evidence for one actually slotted saved-build skill."""

    bar: str
    slot: int
    kind: RotationActionKind
    skill_name: str
    duration_resolution: RotationDurationResolution

    @property
    def canonical_durations_seconds(self) -> tuple[float, ...]:
        return tuple(
            sorted(
                {
                    evidence.duration_seconds
                    for evidence in self.duration_resolution.evidence
                }
            )
        )


@dataclass(frozen=True)
class SavedBuildRotationTimingAudit:
    """Role-neutral timing evidence inventory for one real saved build.

    This is intentionally an evidence audit, not a rotation recommendation.
    It reports what is slotted and which positive canonical effect durations are
    known. It does not infer recast intervals, priorities, weaving, or healing /
    damage consequences.
    """

    character_name: str
    build_name: str
    role: str
    skills: tuple[SavedBuildSkillTimingEvidence, ...]
    unresolved: tuple[str, ...] = ()


def audit_saved_build_rotation_timing(
    build: PlayerBuild,
    *,
    database_path: str | Path = DEFAULT_DATABASE,
    duration_resolver: Callable[[str], RotationDurationResolution] | None = None,
) -> SavedBuildRotationTimingAudit:
    """Inventory canonical duration evidence for every slotted saved-build skill."""

    if duration_resolver is None:
        def duration_resolver(skill_name: str) -> RotationDurationResolution:
            return resolve_rotation_duration_evidence(
                skill_name,
                database_path=database_path,
            )

    skills: list[SavedBuildSkillTimingEvidence] = []
    unresolved: list[str] = []

    for bar, saved_skills in (
        ("front", tuple(build.FrontBarSkills)),
        ("back", tuple(build.BackBarSkills)),
    ):
        for index, raw_name in enumerate(saved_skills[:6], start=1):
            skill_name = str(raw_name or "").strip()
            if not skill_name:
                continue

            kind = (
                RotationActionKind.ULTIMATE
                if index == 6
                else RotationActionKind.SKILL
            )
            resolution = duration_resolver(skill_name)
            skills.append(
                SavedBuildSkillTimingEvidence(
                    bar=bar,
                    slot=index,
                    kind=kind,
                    skill_name=skill_name,
                    duration_resolution=resolution,
                )
            )
            unresolved.extend(
                f"{bar} slot {index} {skill_name}: {message}"
                for message in resolution.unresolved
            )

    return SavedBuildRotationTimingAudit(
        character_name=str(build.Name or "").strip(),
        build_name=str(build.BuildName or "").strip(),
        role=str(build.Role or "").strip(),
        skills=tuple(skills),
        unresolved=tuple(unresolved),
    )
