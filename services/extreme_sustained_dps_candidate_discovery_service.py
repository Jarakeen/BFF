from __future__ import annotations

"""Discover canonical saved DD build/rotation witnesses for sustained-DPS search."""

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
)
from services.build_service import BuildService


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


@dataclass(frozen=True)
class ExtremeSustainedDPSDiscoveryCandidate:
    build: PlayerBuild
    build_id: str
    label: str
    rotation_duration_seconds: float


@dataclass(frozen=True)
class ExtremeSustainedDPSDiscoveryExclusion:
    label: str
    reason: str
    build_id: str = ""
    blocking: bool = True


@dataclass(frozen=True)
class ExtremeSustainedDPSDiscoveryResult:
    candidates: tuple[ExtremeSustainedDPSDiscoveryCandidate, ...]
    exclusions: tuple[ExtremeSustainedDPSDiscoveryExclusion, ...]
    evidence: tuple[str, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


class ExtremeSustainedDPSCandidateDiscoveryService:
    """Discover saved DD builds that have canonical saved RotationPlan evidence."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        build_service: BuildService | None = None,
        artifact_service: BuildRotationArtifactService | None = None,
        catalog_service=None,
    ) -> None:
        self.database_path = Path(database_path)
        data_dir = self.database_path.parent
        self.build_service = build_service or BuildService(data_dir / "builds.json")
        self.catalog_service = (
            catalog_service
            or self.build_service.canonical.catalog_service
        )
        self.artifact_service = artifact_service or BuildRotationArtifactService(
            data_dir / "build_rotations.json"
        )

    @staticmethod
    def _normalized_role(build: PlayerBuild) -> str:
        return " ".join(
            str(getattr(build, "Role", "") or "")
            .strip()
            .casefold()
            .replace("_", " ")
            .split()
        )

    @staticmethod
    def _label(build: PlayerBuild, index: int) -> str:
        character = str(getattr(build, "Name", "") or "").strip()
        build_name = str(getattr(build, "BuildName", "") or "").strip()
        explicit_id = str(getattr(build, "BuildId", "") or "").strip()
        if character and build_name:
            return f"{character} — {build_name}"
        if build_name:
            return build_name
        if character:
            return character
        if explicit_id:
            return explicit_id
        return f"Saved build {index + 1}"

    def discover(self) -> ExtremeSustainedDPSDiscoveryResult:
        roster = self.build_service.load()
        candidates: list[ExtremeSustainedDPSDiscoveryCandidate] = []
        exclusions: list[ExtremeSustainedDPSDiscoveryExclusion] = []

        for index, build in enumerate(tuple(roster.Members)):
            label = self._label(build, index)
            role = self._normalized_role(build)
            if role not in _DD_ROLE_KEYS:
                exclusions.append(
                    ExtremeSustainedDPSDiscoveryExclusion(
                        label=label,
                        build_id=str(getattr(build, "BuildId", "") or "").strip(),
                        reason="saved build is not explicitly DD/DPS role",
                        blocking=False,
                    )
                )
                continue

            build_id = resolve_canonical_build_id(self.catalog_service, build)
            if not build_id:
                exclusions.append(
                    ExtremeSustainedDPSDiscoveryExclusion(
                        label=label,
                        build_id=str(getattr(build, "BuildId", "") or "").strip(),
                        reason="canonical build identity is missing, stale, or ambiguous",
                    )
                )
                continue

            try:
                plan = self.artifact_service.get_rotation_plan(build_id)
            except ValueError as exc:
                exclusions.append(
                    ExtremeSustainedDPSDiscoveryExclusion(
                        label=label,
                        build_id=build_id,
                        reason=f"saved RotationPlan artifact is invalid: {exc}",
                    )
                )
                continue

            if plan is None:
                exclusions.append(
                    ExtremeSustainedDPSDiscoveryExclusion(
                        label=label,
                        build_id=build_id,
                        reason="no saved canonical RotationPlan artifact",
                    )
                )
                continue

            candidates.append(
                ExtremeSustainedDPSDiscoveryCandidate(
                    build=build,
                    build_id=build_id,
                    label=label,
                    rotation_duration_seconds=float(plan.duration_seconds),
                )
            )

        ordered_candidates = tuple(
            sorted(
                candidates,
                key=lambda row: (
                    row.label.casefold(),
                    row.build_id,
                ),
            )
        )
        ordered_exclusions = tuple(
            sorted(
                exclusions,
                key=lambda row: (
                    row.label.casefold(),
                    row.build_id,
                    row.reason.casefold(),
                ),
            )
        )
        evidence = (
            f"Scanned {len(tuple(roster.Members))} canonical saved build rows",
            f"Discovered {len(ordered_candidates)} DD/DPS builds with saved RotationPlan evidence",
            f"Excluded {len(ordered_exclusions)} saved build rows with explicit reasons",
        )
        return ExtremeSustainedDPSDiscoveryResult(
            candidates=ordered_candidates,
            exclusions=ordered_exclusions,
            evidence=evidence,
        )


__all__ = [
    "ExtremeSustainedDPSCandidateDiscoveryService",
    "ExtremeSustainedDPSDiscoveryCandidate",
    "ExtremeSustainedDPSDiscoveryExclusion",
    "ExtremeSustainedDPSDiscoveryResult",
]
