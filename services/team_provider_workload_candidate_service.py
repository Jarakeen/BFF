from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.character_progression import CharacterProgression
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.team_provider_canonical_workload_service import (
    TeamProviderCanonicalActionReference,
    TeamProviderCanonicalContribution,
    TeamProviderCanonicalWorkloadProjection,
    TeamProviderCanonicalWorkloadService,
)
from services.team_provider_coverage_service import TeamProviderCoverageResult
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageResult,
)


def _identity(character_name: object, build_name: object) -> tuple[str, str]:
    return (
        str(character_name or "").strip().casefold(),
        str(build_name or "").strip().casefold(),
    )


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class TeamProviderActionBinding:
    """Exact saved-build action declared to produce one provider effect."""

    character_name: str
    build_name: str
    action_name: str
    primary_role_displacement_seconds: float | None = None

    def __post_init__(self) -> None:
        for field_name in ("character_name", "build_name", "action_name"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"provider action binding {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        if self.primary_role_displacement_seconds is not None:
            displacement = float(self.primary_role_displacement_seconds)
            if not isfinite(displacement) or displacement < 0:
                raise ValueError(
                    "primary-role displacement must be finite and non-negative"
                )
            object.__setattr__(
                self, "primary_role_displacement_seconds", displacement
            )


@dataclass(frozen=True)
class TeamProviderWorkloadAlternativeRequest:
    """One explicit team provider strategy ready for canonical workload projection."""

    alternative_id: str
    effect_key: str
    duration_seconds: float
    recipient_coverage_result: TeamProviderCoverageResult
    temporal_coverage_result: TeamProviderTemporalCoverageResult
    action_bindings: tuple[TeamProviderActionBinding, ...]
    gcd_seconds_per_application: float | None

    def __post_init__(self) -> None:
        alternative = str(self.alternative_id or "").strip()
        if not alternative:
            raise ValueError("provider workload alternative_id must be non-empty")
        object.__setattr__(self, "alternative_id", alternative)

        effect = str(self.effect_key or "").strip()
        if not effect or effect != _canonical(effect):
            raise ValueError("provider workload effect_key must be lower-snake-case")
        object.__setattr__(self, "effect_key", effect)

        duration = float(self.duration_seconds)
        if not isfinite(duration) or duration <= 0:
            raise ValueError("provider workload duration_seconds must be positive")
        object.__setattr__(self, "duration_seconds", duration)

        if _canonical(self.temporal_coverage_result.effect_key) != effect:
            raise ValueError("temporal coverage result must describe the requested effect")

        if not self.action_bindings:
            raise ValueError("provider workload alternative requires action bindings")


@dataclass(frozen=True)
class TeamProviderWorkloadCandidateRejection:
    alternative_id: str
    effect_key: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class TeamProviderWorkloadCandidateResult:
    projections: tuple[TeamProviderCanonicalWorkloadProjection, ...]
    rejected: tuple[TeamProviderWorkloadCandidateRejection, ...]

    @property
    def workloads(self):
        return tuple(item.workload for item in self.projections)


class TeamProviderWorkloadCandidateService:
    """Project explicit provider alternatives for the currently selected team.

    The service performs identity and scheduled-action binding only. It never infers
    an effect from a skill name, a role, gear, or static capability availability.
    A requested contributor must be an exact selected saved build with one exact
    matching RotationPlan. Every matching scheduled cast is retained so refresh
    workload is measured from the plan rather than from a single representative cast.
    """

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE,
        *,
        canonical_workload: TeamProviderCanonicalWorkloadService | None = None,
    ) -> None:
        self.canonical_workload = (
            canonical_workload or TeamProviderCanonicalWorkloadService(database_path)
        )

    def generate(
        self,
        *,
        selected_builds: tuple[PlayerBuild, ...],
        rotation_plans: tuple[RotationPlan, ...],
        progression_by_identity: dict[tuple[str, str], CharacterProgression],
        alternatives: tuple[TeamProviderWorkloadAlternativeRequest, ...],
    ) -> TeamProviderWorkloadCandidateResult:
        builds, build_issues = self._unique_builds(selected_builds)
        plans, plan_issues = self._unique_plans(rotation_plans)
        normalized_progression = {
            _identity(*key): value for key, value in progression_by_identity.items()
        }

        projections: list[TeamProviderCanonicalWorkloadProjection] = []
        rejected: list[TeamProviderWorkloadCandidateRejection] = []
        for alternative in alternatives:
            blockers = [*build_issues, *plan_issues]
            references_by_identity: dict[
                tuple[str, str], list[TeamProviderCanonicalActionReference]
            ] = {}

            for binding in alternative.action_bindings:
                key = _identity(binding.character_name, binding.build_name)
                build = builds.get(key)
                plan = plans.get(key)
                progression = normalized_progression.get(key)
                label = f"{binding.character_name} / {binding.build_name}"
                if build is None:
                    blockers.append(f"{label}: contributor is not an exact selected saved build")
                    continue
                if plan is None:
                    blockers.append(f"{label}: no exact rotation plan is attached")
                    continue
                if progression is None:
                    blockers.append(f"{label}: character progression evidence is not attached")
                    continue
                matches = tuple(
                    action
                    for action in plan.actions
                    if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
                    and str(action.name or "").strip().casefold()
                    == binding.action_name.casefold()
                )
                if not matches:
                    blockers.append(
                        f"{label}: {binding.action_name!r} is not scheduled in the attached plan"
                    )
                    continue
                references_by_identity.setdefault(key, []).extend(
                    TeamProviderCanonicalActionReference(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        primary_role_displacement_seconds=(
                            binding.primary_role_displacement_seconds
                        ),
                    )
                    for action in matches
                )

            if blockers:
                rejected.append(
                    TeamProviderWorkloadCandidateRejection(
                        alternative_id=alternative.alternative_id,
                        effect_key=alternative.effect_key,
                        blockers=tuple(dict.fromkeys(blockers)),
                    )
                )
                continue

            contributions = tuple(
                TeamProviderCanonicalContribution(
                    build=builds[key],
                    progression=normalized_progression[key],
                    plan=plans[key],
                    provider_actions=tuple(
                        sorted(
                            references,
                            key=lambda item: (item.time_seconds, item.sequence),
                        )
                    ),
                )
                for key, references in sorted(references_by_identity.items())
            )
            projections.append(
                self.canonical_workload.project_from_coverage(
                    alternative_id=alternative.alternative_id,
                    effect_key=alternative.effect_key,
                    duration_seconds=alternative.duration_seconds,
                    recipient_coverage_result=alternative.recipient_coverage_result,
                    temporal_coverage_result=alternative.temporal_coverage_result,
                    contributions=contributions,
                    gcd_seconds_per_application=(
                        alternative.gcd_seconds_per_application
                    ),
                )
            )

        return TeamProviderWorkloadCandidateResult(
            projections=tuple(projections),
            rejected=tuple(rejected),
        )

    @staticmethod
    def _unique_builds(
        builds: tuple[PlayerBuild, ...],
    ) -> tuple[dict[tuple[str, str], PlayerBuild], tuple[str, ...]]:
        indexed: dict[tuple[str, str], PlayerBuild] = {}
        issues: list[str] = []
        for build in builds:
            key = _identity(getattr(build, "Name", ""), getattr(build, "BuildName", ""))
            if not all(key):
                issues.append(
                    "selected team contains a build without exact character/build identity"
                )
            elif key in indexed:
                issues.append(f"selected team repeats saved build identity: {key[0]} / {key[1]}")
            else:
                indexed[key] = build
        return indexed, tuple(issues)

    @staticmethod
    def _unique_plans(
        plans: tuple[RotationPlan, ...],
    ) -> tuple[dict[tuple[str, str], RotationPlan], tuple[str, ...]]:
        indexed: dict[tuple[str, str], RotationPlan] = {}
        issues: list[str] = []
        for plan in plans:
            key = _identity(plan.character_name, plan.build_name)
            if key in indexed:
                issues.append(f"multiple rotation plans are attached for: {key[0]} / {key[1]}")
            else:
                indexed[key] = plan
        return indexed, tuple(issues)


__all__ = [
    "TeamProviderActionBinding",
    "TeamProviderWorkloadAlternativeRequest",
    "TeamProviderWorkloadCandidateRejection",
    "TeamProviderWorkloadCandidateResult",
    "TeamProviderWorkloadCandidateService",
]
