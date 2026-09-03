from __future__ import annotations

"""Difficulty-aware availability of source-backed encounter handling methods.

This layer does not invent alternate strategies. It only records when structured
encounter evidence says a known interaction is unavailable at a selected
difficulty. When a known solution is disabled and no alternate is proven, the
execution result becomes UNKNOWN rather than MISSING.
"""

from dataclasses import dataclass

from services.encounter_difficulty import EncounterDifficulty, normalize_encounter_difficulty
from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterExecutionAvailability:
    encounter_id: str
    mechanic_name: str
    interaction: str
    difficulty: EncounterDifficulty
    available: bool | None
    fact_id: str
    reconciliation_status: str
    distinct_sources: int
    explanation: str


class EncounterExecutionAvailabilityService:
    """Resolve interaction availability only from exact structured evidence."""

    EXPLICIT_FACT_TYPE = "execution_availability"
    LEGACY_FACT_TYPE = "mechanic_detail"
    OAX_HM_FACT_KEY = "hardmode_magma_sludge_disables_cleanse_pools_alcast"
    OAX_HM_FIELD = "magma_sludge_disables_cleanse_pools"

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    def rows(
        self,
        encounter_id: str,
        difficulty: EncounterDifficulty | str,
    ) -> tuple[EncounterExecutionAvailability, ...]:
        selected = normalize_encounter_difficulty(difficulty)
        explicit = self._encounter_service.evidence_facts(
            encounter_id,
            fact_type=self.EXPLICIT_FACT_TYPE,
        )
        if explicit:
            output: list[EncounterExecutionAvailability] = []
            for fact in explicit:
                value = fact.value
                if not isinstance(value, dict):
                    continue
                try:
                    fact_difficulty = normalize_encounter_difficulty(
                        str(value.get("difficulty") or "")
                    )
                except ValueError:
                    continue
                if fact_difficulty is not selected:
                    continue
                interaction = str(value.get("interaction") or "").strip()
                if not interaction:
                    continue
                available_raw = value.get("available")
                available = available_raw if isinstance(available_raw, bool) else None
                if fact.status == "conflicting":
                    available = None
                output.append(
                    EncounterExecutionAvailability(
                        encounter_id=encounter_id,
                        mechanic_name=str(value.get("mechanic_name") or fact.fact_key).strip(),
                        interaction=interaction,
                        difficulty=selected,
                        available=available,
                        fact_id=fact.fact_id,
                        reconciliation_status=fact.status,
                        distinct_sources=fact.distinct_sources,
                        explanation=str(value.get("explanation") or "").strip(),
                    )
                )
            return tuple(output)

        if selected is not EncounterDifficulty.HARDMODE:
            return ()

        output = []
        for fact in self._encounter_service.evidence_facts(
            encounter_id,
            fact_type=self.LEGACY_FACT_TYPE,
        ):
            if fact.fact_key != self.OAX_HM_FACT_KEY:
                continue
            value = fact.value
            if not isinstance(value, dict) or value.get(self.OAX_HM_FIELD) is not True:
                continue
            available = None if fact.status == "conflicting" else False
            output.append(
                EncounterExecutionAvailability(
                    encounter_id=encounter_id,
                    mechanic_name="Noxious Sludge",
                    interaction="cleanse_pool",
                    difficulty=selected,
                    available=available,
                    fact_id=fact.fact_id,
                    reconciliation_status=fact.status,
                    distinct_sources=fact.distinct_sources,
                    explanation=(
                        "Hard Mode evidence says Magma Sludge disables the cleanse pools. "
                        "No alternate cleanse interaction is promoted from this fact."
                    ),
                )
            )
        return tuple(output)
