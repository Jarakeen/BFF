from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from .rotation_duration_evidence import (
    RotationDurationEvidence,
    RotationDurationResolution,
    resolve_rotation_duration_evidence,
)
from .rotation_plan import RotationActionKind
from .semi_static_rotation import SemiStaticRotationEntry
from .skill_effect_repository import DEFAULT_DATABASE


@dataclass(frozen=True)
class SemiStaticRecastEvidence:
    """Canonical duration evidence associated with one manual skill recast.

    A duration match is descriptive evidence only. It does not promote a
    caller-supplied semi-static recast interval into a canonical rotation rule.
    """

    skill_name: str
    recast_interval_seconds: float
    duration_resolution: RotationDurationResolution
    matching_evidence: tuple[RotationDurationEvidence, ...] = ()

    @property
    def canonical_durations_seconds(self) -> tuple[float, ...]:
        return tuple(
            sorted(
                {
                    item.duration_seconds
                    for item in self.duration_resolution.evidence
                }
            )
        )

    @property
    def matches_canonical_duration(self) -> bool:
        return bool(self.matching_evidence)


def assess_semi_static_recast_evidence(
    entry: SemiStaticRotationEntry,
    *,
    database_path: str | Path = DEFAULT_DATABASE,
) -> SemiStaticRecastEvidence | None:
    """Attach canonical duration evidence to one repeating skill entry.

    Non-skill actions and one-shot skill actions have no duration-based recast
    claim to assess, so they return ``None``. Repeating skill entries resolve
    all known positive duration-bearing effects and report which, if any,
    exactly align with the manual recast interval.
    """

    if entry.kind is not RotationActionKind.SKILL:
        return None
    if entry.recast_interval_seconds is None:
        return None
    if entry.name is None:
        # SemiStaticRotationEntry validation should already prevent this, but
        # keep this adapter defensive because it is a public Phase 13 boundary.
        return None

    resolution = resolve_rotation_duration_evidence(
        entry.name,
        database_path=database_path,
    )
    interval = float(entry.recast_interval_seconds)
    matching = tuple(
        evidence
        for evidence in resolution.evidence
        if math.isclose(
            evidence.duration_seconds,
            interval,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
    )

    return SemiStaticRecastEvidence(
        skill_name=resolution.skill_name or entry.name,
        recast_interval_seconds=interval,
        duration_resolution=resolution,
        matching_evidence=matching,
    )


def assess_semi_static_rotation_recasts(
    entries: tuple[SemiStaticRotationEntry, ...],
    *,
    database_path: str | Path = DEFAULT_DATABASE,
) -> tuple[SemiStaticRecastEvidence, ...]:
    """Resolve duration evidence for every repeating skill in entry order."""

    assessments: list[SemiStaticRecastEvidence] = []
    for entry in entries:
        assessment = assess_semi_static_recast_evidence(
            entry,
            database_path=database_path,
        )
        if assessment is not None:
            assessments.append(assessment)
    return tuple(assessments)
