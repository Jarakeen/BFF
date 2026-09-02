from __future__ import annotations

"""Domain-facing read-only encounter service.

Numeric source values retain their exact source text.  A number is exposed only
when its format is unambiguous; callers must handle unresolved values explicitly.
"""

from dataclasses import dataclass
import re

from services.encounter_projection import EncounterDefinition
from services.encounter_repository import EncounterRepository

_HEALTH = re.compile(r"^\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\s*\(([^()]*)\))?\s*$")

@dataclass(frozen=True)
class EncounterHealth:
    difficulty: str
    raw_value: str
    value: int | None
    annotation: str
    resolution: str

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
        return EncounterHealth(difficulty, raw, int(match.group(1).replace(",", "")), match.group(2) or "", "parsed")
