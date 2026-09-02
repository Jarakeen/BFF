from __future__ import annotations

"""Domain-facing read-only encounter service.

Numeric source values retain their exact source text. A number is exposed only
when its format is unambiguous; callers must handle unresolved values explicitly.
Encounter requirements and target counts are projected only from explicit
structured mechanic fields; this service never derives them from prose.
"""

from dataclasses import dataclass
import re

from services.encounter_projection import EncounterDefinition
from services.encounter_repository import EncounterRepository

_HEALTH = re.compile(r"^\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\s*\(([^()]*)\))?\s*$")
_PERCENT = re.compile(r"^\s*(100|[1-9]?\d)\s*%\s*$")


@dataclass(frozen=True)
class EncounterHealth:
    difficulty: str
    raw_value: str
    value: int | None
    annotation: str
    resolution: str


@dataclass(frozen=True)
class EncounterPhaseThreshold:
    phase_id: str
    raw_value: str
    percent: int | None
    resolution: str


@dataclass(frozen=True)
class EncounterRequirement:
    """One explicit mechanic demand, without provider or strategy assignment."""

    requirement_id: str
    encounter_id: str
    mechanic_id: str
    mechanic_name: str
    requirement_type: str
    target_count: int | None
    interpretation_status: str


@dataclass(frozen=True)
class EncounterTargetConstraint:
    """An explicit mechanic target count, not a target-selection decision."""

    constraint_id: str
    encounter_id: str
    mechanic_id: str
    mechanic_name: str
    target_count: int
    interpretation_status: str


class EncounterService:
    def __init__(self, repository: EncounterRepository) -> None:
        self._repository = repository

    def encounter_ids(self) -> tuple[str, ...]:
        return self._repository.encounter_ids()

    def get(self, encounter_id: str) -> EncounterDefinition:
        return self._repository.get(encounter_id)

    def health(self, encounter_id: str, difficulty: str) -> EncounterHealth:
        if difficulty not in {"normal", "veteran", "hardmode"}:
            raise ValueError("difficulty must be normal, veteran, or hardmode")
        encounter = self.get(encounter_id)
        raw = dict(encounter.difficulty_health).get(difficulty, "")
        match = _HEALTH.fullmatch(raw)
        if match is None:
            return EncounterHealth(difficulty, raw, None, "", "unresolved")
        return EncounterHealth(
            difficulty,
            raw,
            int(match.group(1).replace(",", "")),
            match.group(2) or "",
            "parsed",
        )

    def phase_threshold(self, encounter_id: str, phase_id: str) -> EncounterPhaseThreshold:
        if not isinstance(phase_id, str) or not phase_id:
            raise ValueError("phase_id must be a non-empty canonical id")
        encounter = self.get(encounter_id)
        phase = next((item for item in encounter.phases if item.phase_id == phase_id), None)
        if phase is None:
            raise LookupError(f"No canonical phase {phase_id!r} for encounter {encounter_id!r}")
        match = _PERCENT.fullmatch(phase.threshold)
        return EncounterPhaseThreshold(
            phase_id=phase.phase_id,
            raw_value=phase.threshold,
            percent=int(match.group(1)) if match else None,
            resolution="parsed" if match else "unresolved",
        )

    def requirements(self, encounter_id: str) -> tuple[EncounterRequirement, ...]:
        """Return demands represented explicitly by structured mechanic fields.

        ``None`` and ``False`` do not become requirements. In particular, prose
        such as "should be dodged" does not create an invented ``dodge`` demand
        because the current canonical mechanic contract has no structured dodge
        field. Later phases may evaluate these requirements, but this method does
        not choose a provider, player, target, position, or response.
        """
        encounter = self.get(encounter_id)
        requirements = []
        for mechanic in encounter.mechanics:
            structured_demands = (
                ("movement", mechanic.requires_movement),
                ("positioning", mechanic.requires_positioning),
                ("cleanse", mechanic.requires_cleanse),
                ("interrupt", mechanic.interruptible),
            )
            for requirement_type, required in structured_demands:
                if required is not True:
                    continue
                requirements.append(
                    EncounterRequirement(
                        requirement_id=f"{mechanic.mechanic_id}:requirement:{requirement_type}",
                        encounter_id=encounter.encounter_id,
                        mechanic_id=mechanic.mechanic_id,
                        mechanic_name=mechanic.name,
                        requirement_type=requirement_type,
                        target_count=mechanic.target_count,
                        interpretation_status=mechanic.interpretation_status,
                    )
                )
        return tuple(requirements)

    def target_constraints(self, encounter_id: str) -> tuple[EncounterTargetConstraint, ...]:
        """Return only explicit positive target counts from structured mechanics.

        A count does not identify which players or enemies are chosen, nor does
        it imply a targeting rule. Missing target counts remain absent rather
        than being converted to one, all players, or any other guessed value.
        """
        encounter = self.get(encounter_id)
        constraints = []
        for mechanic in encounter.mechanics:
            target_count = mechanic.target_count
            if not isinstance(target_count, int) or isinstance(target_count, bool) or target_count <= 0:
                continue
            constraints.append(
                EncounterTargetConstraint(
                    constraint_id=f"{mechanic.mechanic_id}:targets",
                    encounter_id=encounter.encounter_id,
                    mechanic_id=mechanic.mechanic_id,
                    mechanic_name=mechanic.name,
                    target_count=target_count,
                    interpretation_status=mechanic.interpretation_status,
                )
            )
        return tuple(constraints)
