from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from engine.config import DEFAULT_DATABASE
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.saved_build_adapter import (
    SavedBuildAdaptation,
    SavedBuildCharacterAdapter,
)
from models.build_model import PlayerBuild
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeAssessment,
    RotationEffectUptimeRequirement,
    RotationEffectUptimeService,
)
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadencePlanCandidate,
)


class _SavedBuildAdapter(Protocol):
    def adapt(
        self,
        saved: PlayerBuild,
        *,
        character_id: str | None = None,
    ) -> SavedBuildAdaptation: ...


class _EffectUptimeEvaluator(Protocol):
    def assess(
        self,
        *,
        plan,
        build: CharacterBuild,
        requirements: tuple[RotationEffectUptimeRequirement, ...],
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationEffectUptimeAssessment, ...]: ...


@dataclass(frozen=True)
class RotationSupportCadenceEffectEvidence:
    """Build-aware effect evidence for one complete cadence candidate set."""

    assessments_by_candidate: dict[
        str, tuple[RotationEffectUptimeAssessment, ...]
    ]
    canonical_build: CharacterBuild | None
    unresolved: tuple[str, ...] = ()


class RotationSupportCadenceEffectEvidenceService:
    """Recompute cast-produced effect uptime for every generated rotation candidate.

    Progressive optimization must not reuse effect-uptime measurements after the
    promoted rotation changes. This adapter converts the saved PlayerBuild once into
    the canonical CharacterBuild, then delegates every candidate plan to the existing
    RotationEffectUptimeService. Gear/set duration modifiers and caller-supplied
    passive grants therefore stay in the canonical build-aware mechanics path.

    If canonical build adaptation fails, every candidate receives unresolved
    assessments for the supplied requirements. The service does not silently drop
    those hard obligations merely because the legacy build could not be resolved.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        build_adapter: _SavedBuildAdapter | None = None,
        uptime_service: _EffectUptimeEvaluator | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(
            self.database_path
        )
        self.uptime_service = uptime_service or RotationEffectUptimeService()

    def assess(
        self,
        *,
        build: PlayerBuild,
        candidates: tuple[RotationSupportCadencePlanCandidate, ...],
        requirements: tuple[RotationEffectUptimeRequirement, ...],
        passives: Iterable[PassiveGrant] = (),
        character_id: str | None = None,
    ) -> RotationSupportCadenceEffectEvidence:
        self._validate_candidate_ids(candidates)
        adaptation = self.build_adapter.adapt(build, character_id=character_id)
        unresolved = self._dedupe(tuple(adaptation.unresolved))
        passive_tuple = tuple(passives)

        if not requirements:
            return RotationSupportCadenceEffectEvidence(
                assessments_by_candidate={candidate.candidate_id: () for candidate in candidates},
                canonical_build=adaptation.build,
                unresolved=unresolved,
            )

        if adaptation.build is None:
            details = "; ".join(unresolved) or "canonical saved-build adaptation failed"
            return RotationSupportCadenceEffectEvidence(
                assessments_by_candidate={
                    candidate.candidate_id: tuple(
                        RotationEffectUptimeAssessment(
                            requirement=requirement,
                            summary=None,
                            unresolved=(details,),
                        )
                        for requirement in requirements
                    )
                    for candidate in candidates
                },
                canonical_build=None,
                unresolved=unresolved or (details,),
            )

        assessments: dict[str, tuple[RotationEffectUptimeAssessment, ...]] = {}
        for candidate in candidates:
            assessments[candidate.candidate_id] = self.uptime_service.assess(
                plan=candidate.plan,
                build=adaptation.build,
                requirements=requirements,
                passives=passive_tuple,
            )

        return RotationSupportCadenceEffectEvidence(
            assessments_by_candidate=assessments,
            canonical_build=adaptation.build,
            unresolved=unresolved,
        )

    @staticmethod
    def _validate_candidate_ids(
        candidates: tuple[RotationSupportCadencePlanCandidate, ...],
    ) -> None:
        seen: set[str] = set()
        for candidate in candidates:
            candidate_id = str(candidate.candidate_id or "").strip()
            if not candidate_id:
                raise ValueError("support cadence effect evidence candidate_id must be non-empty")
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate support cadence effect evidence candidate_id: {candidate_id!r}"
                )
            seen.add(key)

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = [
    "RotationSupportCadenceEffectEvidence",
    "RotationSupportCadenceEffectEvidenceService",
]
