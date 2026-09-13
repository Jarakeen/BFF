from __future__ import annotations

"""Discover saved DD builds that can serve as execute evidence controls.

This service is read-only. It classifies ordinary slotted skills through the canonical
execute evidence disposition service and reports whether a saved DD build contains a
scheduler-supported threshold execute, unresolved continuous amplification, or neither.
It does not mutate builds, schedule rotations, or reinterpret missing evidence.
"""

from dataclasses import dataclass

from services.rotation_execute_evidence_disposition_service import (
    RotationExecuteEvidenceDisposition,
    RotationExecuteEvidenceDispositionResult,
    RotationExecuteEvidenceDispositionService,
)


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


@dataclass(frozen=True)
class RotationExecuteSavedBuildSkillDisposition:
    bar: str
    slot: int
    skill_name: str
    result: RotationExecuteEvidenceDispositionResult


@dataclass(frozen=True)
class RotationExecuteSavedBuildControl:
    character_name: str
    build_name: str
    role: str
    skills: tuple[RotationExecuteSavedBuildSkillDisposition, ...]

    @property
    def threshold_supported(self) -> tuple[RotationExecuteSavedBuildSkillDisposition, ...]:
        return tuple(
            row
            for row in self.skills
            if row.result.disposition
            is RotationExecuteEvidenceDisposition.THRESHOLD_ACTIVATION_SUPPORTED
        )

    @property
    def continuous_unresolved(self) -> tuple[RotationExecuteSavedBuildSkillDisposition, ...]:
        return tuple(
            row
            for row in self.skills
            if row.result.disposition
            is RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_UNRESOLVED
        )

    @property
    def is_positive_threshold_control(self) -> bool:
        return bool(self.threshold_supported)


class RotationExecuteSavedBuildControlDiscoveryService:
    """Classify saved DD builds for positive execute-control suitability."""

    def __init__(
        self,
        *,
        disposition_service: RotationExecuteEvidenceDispositionService | None = None,
    ) -> None:
        self.disposition_service = (
            disposition_service or RotationExecuteEvidenceDispositionService()
        )

    def discover(self, builds) -> tuple[RotationExecuteSavedBuildControl, ...]:
        controls: list[RotationExecuteSavedBuildControl] = []
        for build in builds:
            role = str(getattr(build, "Role", "") or "").strip()
            if role.casefold() not in _DD_ROLE_KEYS:
                continue
            skills: list[RotationExecuteSavedBuildSkillDisposition] = []
            for bar, attribute in (("front", "FrontBarSkills"), ("back", "BackBarSkills")):
                values = list(getattr(build, attribute, []) or [])[:5]
                for slot, raw in enumerate(values, start=1):
                    skill_name = str(raw or "").strip()
                    if not skill_name:
                        continue
                    skills.append(
                        RotationExecuteSavedBuildSkillDisposition(
                            bar=bar,
                            slot=slot,
                            skill_name=skill_name,
                            result=self.disposition_service.resolve(skill_name),
                        )
                    )
            controls.append(
                RotationExecuteSavedBuildControl(
                    character_name=str(getattr(build, "Name", "") or "").strip(),
                    build_name=str(getattr(build, "BuildName", "") or "").strip(),
                    role=role,
                    skills=tuple(skills),
                )
            )
        controls.sort(
            key=lambda row: (
                not row.is_positive_threshold_control,
                row.character_name.casefold(),
                row.build_name.casefold(),
            )
        )
        return tuple(controls)


__all__ = [
    "RotationExecuteSavedBuildControl",
    "RotationExecuteSavedBuildControlDiscoveryService",
    "RotationExecuteSavedBuildSkillDisposition",
]
