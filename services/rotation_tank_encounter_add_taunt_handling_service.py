from __future__ import annotations

"""Read encounter-specific reviewed add-taunt handling semantics.

This layer is deliberately softer than mechanic truth. It records reviewed behavior
from observed taunt-state occupancy and may inform Tank candidate ranking/context, but
single-report evidence cannot become an exact hard uptime floor.
"""

from dataclasses import dataclass
import json
from pathlib import Path

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "encounter_add_taunt_handling"
    / "reviewed.json"
)

_ALLOWED_HANDLING = {
    "strong_taunt_maintenance_target",
    "selective_contextual_taunt_target",
}


@dataclass(frozen=True)
class ReviewedAddTauntHandlingActor:
    actor_name: str
    observed_instances: int
    untaunted_instances: int
    multi_source_instances: int
    median_coverage_fraction: float
    minimum_coverage_fraction: float
    maximum_coverage_fraction: float
    handling_class: str
    ranking_context: bool
    hard_maintenance_policy: bool
    interpretation: str

    def __post_init__(self) -> None:
        name = str(self.actor_name or "").strip()
        interpretation = str(self.interpretation or "").strip()
        if not name or not interpretation:
            raise ValueError("reviewed add-taunt handling actor fields must be non-empty")
        if self.observed_instances <= 0:
            raise ValueError("reviewed add-taunt handling observed_instances must be positive")
        if not 0 <= self.untaunted_instances <= self.observed_instances:
            raise ValueError("reviewed add-taunt handling untaunted_instances is invalid")
        if not 0 <= self.multi_source_instances <= self.observed_instances:
            raise ValueError("reviewed add-taunt handling multi_source_instances is invalid")
        if self.handling_class not in _ALLOWED_HANDLING:
            raise ValueError(f"unsupported add-taunt handling_class: {self.handling_class!r}")
        values = (
            float(self.minimum_coverage_fraction),
            float(self.median_coverage_fraction),
            float(self.maximum_coverage_fraction),
        )
        if not (0.0 <= values[0] <= values[1] <= values[2] <= 1.0):
            raise ValueError("reviewed add-taunt coverage must satisfy 0 <= min <= median <= max <= 1")
        if self.hard_maintenance_policy:
            raise ValueError("single-report reviewed add-taunt behavior cannot be hard maintenance policy")
        object.__setattr__(self, "actor_name", name)
        object.__setattr__(self, "interpretation", interpretation)


@dataclass(frozen=True)
class ReviewedEncounterAddTauntHandling:
    encounter_id: str
    evidence_scope: str
    source_report: str
    active_window_semantics: str
    taunt_state_semantics: str
    actors: tuple[ReviewedAddTauntHandlingActor, ...]
    interpretation: str

    def actor(self, actor_name: str) -> ReviewedAddTauntHandlingActor | None:
        key = str(actor_name or "").strip().casefold()
        return next((row for row in self.actors if row.actor_name.casefold() == key), None)


class RotationTankEncounterAddTauntHandlingService:
    def __init__(self, path: str | Path = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._plans = self._load(self.path)

    @classmethod
    def _load(cls, path: Path) -> dict[str, ReviewedEncounterAddTauntHandling]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported reviewed add-taunt handling schema_version")
        raw_encounters = payload.get("encounters")
        if not isinstance(raw_encounters, list):
            raise ValueError("reviewed add-taunt handling encounters must be a list")
        plans: dict[str, ReviewedEncounterAddTauntHandling] = {}
        for raw in raw_encounters:
            actors = tuple(
                ReviewedAddTauntHandlingActor(
                    actor_name=str(actor.get("actor_name") or ""),
                    observed_instances=int(actor.get("observed_instances") or 0),
                    untaunted_instances=int(actor.get("untaunted_instances") or 0),
                    multi_source_instances=int(actor.get("multi_source_instances") or 0),
                    median_coverage_fraction=float(actor.get("median_coverage_fraction") or 0.0),
                    minimum_coverage_fraction=float(actor.get("minimum_coverage_fraction") or 0.0),
                    maximum_coverage_fraction=float(actor.get("maximum_coverage_fraction") or 0.0),
                    handling_class=str(actor.get("handling_class") or ""),
                    ranking_context=bool(actor.get("ranking_context")),
                    hard_maintenance_policy=bool(actor.get("hard_maintenance_policy")),
                    interpretation=str(actor.get("interpretation") or ""),
                )
                for actor in raw.get("actors") or ()
            )
            plan = ReviewedEncounterAddTauntHandling(
                encounter_id=str(raw.get("encounter_id") or "").strip(),
                evidence_scope=str(raw.get("evidence_scope") or "").strip(),
                source_report=str(raw.get("source_report") or "").strip(),
                active_window_semantics=str(raw.get("active_window_semantics") or "").strip(),
                taunt_state_semantics=str(raw.get("taunt_state_semantics") or "").strip(),
                actors=actors,
                interpretation=str(raw.get("interpretation") or "").strip(),
            )
            if not all((plan.encounter_id, plan.evidence_scope, plan.source_report, plan.active_window_semantics, plan.taunt_state_semantics, plan.interpretation)):
                raise ValueError("reviewed add-taunt handling encounter fields must be non-empty")
            if plan.evidence_scope != "single_report_reviewed_behavior":
                raise ValueError(f"unsupported reviewed add-taunt handling evidence_scope: {plan.evidence_scope!r}")
            if not plan.actors:
                raise ValueError("reviewed add-taunt handling encounter requires actors")
            keys = [row.actor_name.casefold() for row in plan.actors]
            if len(keys) != len(set(keys)):
                raise ValueError("reviewed add-taunt handling encounter cannot duplicate actors")
            key = plan.encounter_id.casefold()
            if key in plans:
                raise ValueError(f"duplicate reviewed add-taunt encounter_id: {plan.encounter_id!r}")
            plans[key] = plan
        return plans

    def reviewed_for(self, encounter_id: str) -> ReviewedEncounterAddTauntHandling | None:
        key = str(encounter_id or "").strip().casefold()
        if not key:
            raise ValueError("reviewed add-taunt handling lookup requires encounter_id")
        return self._plans.get(key)


__all__ = [
    "ReviewedAddTauntHandlingActor",
    "ReviewedEncounterAddTauntHandling",
    "RotationTankEncounterAddTauntHandlingService",
]
