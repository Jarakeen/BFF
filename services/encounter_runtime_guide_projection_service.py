from __future__ import annotations

"""Project reviewed runtime observations into read-only encounter-guide notes.

This layer is intentionally presentation-only. Runtime observations describe what
repeatedly happened across reviewed combat telemetry; they are not canonical
mechanics, structural encounter phases, or persisted ``encounter_strategy`` rows.
"""

from dataclasses import dataclass
from pathlib import Path

from services.encounter_runtime_observation_service import (
    EncounterRuntimeObservation,
    EncounterRuntimeObservationService,
)


@dataclass(frozen=True, slots=True)
class EncounterGuideRuntimeNote:
    key: str
    text: str
    confidence: str


@dataclass(frozen=True, slots=True)
class EncounterGuideRuntimeRoleGuidance:
    role: str
    priority: str
    guidance: str


@dataclass(frozen=True, slots=True)
class EncounterGuideRuntimeProjection:
    encounter_id: str
    notes: tuple[EncounterGuideRuntimeNote, ...]
    role_guidance: tuple[EncounterGuideRuntimeRoleGuidance, ...]
    source_labels: tuple[str, ...]
    successful_kills: int
    reviewed_windows: int
    limitations: tuple[str, ...]

    @property
    def has_runtime_evidence(self) -> bool:
        return bool(self.notes or self.role_guidance)


class EncounterRuntimeGuideProjectionService:
    """Read reviewed observation files and expose concise player-facing notes."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = Path(data_root)
        self._loader = EncounterRuntimeObservationService()

    def get(self, encounter_id: str) -> EncounterGuideRuntimeProjection:
        encounter_id = str(encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("encounter_id must be non-empty")

        observations = self._observations(encounter_id)
        if not observations:
            return EncounterGuideRuntimeProjection(
                encounter_id=encounter_id,
                notes=(),
                role_guidance=(),
                source_labels=(),
                successful_kills=0,
                reviewed_windows=0,
                limitations=(),
            )

        notes: list[EncounterGuideRuntimeNote] = []
        guidance: list[EncounterGuideRuntimeRoleGuidance] = []
        source_labels: list[str] = []
        limitations: list[str] = []
        successful_kills = 0
        reviewed_windows = 0

        seen_notes: set[tuple[str, str]] = set()
        seen_guidance: set[tuple[str, str, str]] = set()

        for observation in observations:
            successful_kills += observation.successful_kills
            reviewed_windows += observation.reviewed_window_count
            if observation.source_name not in source_labels:
                source_labels.append(observation.source_name)

            for conclusion in observation.reviewed_conclusions:
                identity = (conclusion.key, conclusion.statement)
                if identity in seen_notes:
                    continue
                seen_notes.add(identity)
                notes.append(
                    EncounterGuideRuntimeNote(
                        key=conclusion.key,
                        text=conclusion.statement,
                        confidence=conclusion.confidence,
                    )
                )

            for implication in observation.strategy_implications:
                identity = (implication.role, implication.priority, implication.guidance)
                if identity in seen_guidance:
                    continue
                seen_guidance.add(identity)
                guidance.append(
                    EncounterGuideRuntimeRoleGuidance(
                        role=implication.role,
                        priority=implication.priority,
                        guidance=implication.guidance,
                    )
                )

            for limitation in observation.limitations:
                if limitation not in limitations:
                    limitations.append(limitation)

        return EncounterGuideRuntimeProjection(
            encounter_id=encounter_id,
            notes=tuple(notes),
            role_guidance=tuple(guidance),
            source_labels=tuple(source_labels),
            successful_kills=successful_kills,
            reviewed_windows=reviewed_windows,
            limitations=tuple(limitations),
        )

    def _observations(self, encounter_id: str) -> tuple[EncounterRuntimeObservation, ...]:
        root = self.data_root / "encounter_observations"
        if not root.exists():
            return ()

        matches: list[EncounterRuntimeObservation] = []
        for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
            observation = self._loader.load(path)
            if observation.encounter_id == encounter_id:
                matches.append(observation)
        return tuple(matches)


__all__ = [
    "EncounterGuideRuntimeNote",
    "EncounterGuideRuntimeProjection",
    "EncounterGuideRuntimeRoleGuidance",
    "EncounterRuntimeGuideProjectionService",
]
