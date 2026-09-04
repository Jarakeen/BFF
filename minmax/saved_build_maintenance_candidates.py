from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationActionKind
from .saved_build_rotation_timing_audit import SavedBuildRotationTimingAudit


@dataclass(frozen=True)
class SavedBuildMaintenanceCandidate:
    """One slotted skill with enough timing evidence to consider for upkeep.

    A candidate is not a recast command. It only says the saved build exposes a
    single unambiguous positive canonical duration for this ordinary skill.
    Encounter pressure, resource state, target state, movement, and role policy
    may all justify casting earlier, later, conditionally, or not at all.
    """

    bar: str
    slot: int
    skill_name: str
    duration_seconds: float
    evidence_sources: tuple[str, ...]


@dataclass(frozen=True)
class SavedBuildMaintenanceCandidateSet:
    candidates: tuple[SavedBuildMaintenanceCandidate, ...]
    unresolved: tuple[str, ...] = ()


def derive_saved_build_maintenance_candidates(
    audit: SavedBuildRotationTimingAudit,
) -> SavedBuildMaintenanceCandidateSet:
    """Surface evidence-backed upkeep candidates without scheduling recasts.

    Ultimates are intentionally excluded from ordinary maintenance. Skills with
    no positive duration or multiple distinct positive durations remain
    unresolved for maintenance-policy purposes rather than being guessed.
    """

    candidates: list[SavedBuildMaintenanceCandidate] = []
    unresolved: list[str] = []

    for skill in audit.skills:
        if skill.kind is not RotationActionKind.SKILL:
            continue

        durations = skill.canonical_durations_seconds
        if not durations:
            unresolved.append(
                f"{skill.bar} slot {skill.slot} {skill.skill_name}: "
                "no canonical duration available for maintenance consideration"
            )
            continue
        if len(durations) != 1:
            rendered = ", ".join(f"{duration:g}s" for duration in durations)
            unresolved.append(
                f"{skill.bar} slot {skill.slot} {skill.skill_name}: "
                f"multiple canonical durations require explicit maintenance policy ({rendered})"
            )
            continue

        duration = durations[0]
        sources = tuple(
            sorted(
                {
                    evidence.source
                    for evidence in skill.duration_resolution.evidence
                    if evidence.duration_seconds == duration
                },
                key=str.casefold,
            )
        )
        candidates.append(
            SavedBuildMaintenanceCandidate(
                bar=skill.bar,
                slot=skill.slot,
                skill_name=skill.skill_name,
                duration_seconds=duration,
                evidence_sources=sources,
            )
        )

    return SavedBuildMaintenanceCandidateSet(
        candidates=tuple(candidates),
        unresolved=tuple(unresolved),
    )
