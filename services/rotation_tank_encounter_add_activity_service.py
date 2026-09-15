from __future__ import annotations

"""Read reviewed encounter add-activity boundary semantics.

This service describes what runtime signal may be used as an observed add-active
boundary for encounter planning. It deliberately does not claim exact spawn time or
exact taunt-required time unless future reviewed evidence proves those stronger
semantics.
"""

from dataclasses import dataclass
import json
from pathlib import Path

from services.paths import DATA


_DEFAULT_PATH = DATA / "encounter_add_activity" / "reviewed.json"


@dataclass(frozen=True)
class ReviewedEncounterAddActivityActor:
    actor_name: str
    activity_boundary: str
    observed_instances: int
    involving_coverage: int
    source_coverage: int
    cast_coverage: int
    interpretation: str

    def __post_init__(self) -> None:
        actor_name = str(self.actor_name or "").strip()
        activity_boundary = str(self.activity_boundary or "").strip()
        interpretation = str(self.interpretation or "").strip()
        if not actor_name:
            raise ValueError("reviewed encounter add activity actor_name must be non-empty")
        if activity_boundary != "earliest_source_or_involving_event":
            raise ValueError(
                "unsupported reviewed encounter add activity boundary: "
                f"{activity_boundary!r}"
            )
        if self.observed_instances <= 0:
            raise ValueError("reviewed encounter add activity observed_instances must be positive")
        for field_name in ("involving_coverage", "source_coverage", "cast_coverage"):
            value = int(getattr(self, field_name))
            if value < 0 or value > self.observed_instances:
                raise ValueError(
                    f"reviewed encounter add activity {field_name} must be within observed instance count"
                )
        if not interpretation:
            raise ValueError("reviewed encounter add activity interpretation must be non-empty")
        object.__setattr__(self, "actor_name", actor_name)
        object.__setattr__(self, "activity_boundary", activity_boundary)
        object.__setattr__(self, "interpretation", interpretation)

    @property
    def fully_observed_source_boundary(self) -> bool:
        return (
            self.involving_coverage == self.observed_instances
            and self.source_coverage == self.observed_instances
        )


@dataclass(frozen=True)
class ReviewedEncounterAddActivityPlan:
    encounter_id: str
    source: str
    actors: tuple[ReviewedEncounterAddActivityActor, ...]

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        source = str(self.source or "").strip()
        if not encounter_id:
            raise ValueError("reviewed encounter add activity encounter_id must be non-empty")
        if not source:
            raise ValueError("reviewed encounter add activity source must be non-empty")
        actors = tuple(self.actors)
        if not actors:
            raise ValueError("reviewed encounter add activity plan requires actors")
        keys = [row.actor_name.casefold() for row in actors]
        if len(keys) != len(set(keys)):
            raise ValueError("reviewed encounter add activity plan cannot duplicate actor_name")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "actors", actors)

    def actor(self, actor_name: str) -> ReviewedEncounterAddActivityActor | None:
        key = str(actor_name or "").strip().casefold()
        for row in self.actors:
            if row.actor_name.casefold() == key:
                return row
        return None


class RotationTankEncounterAddActivityService:
    def __init__(self, path: str | Path = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._plans = self._load(self.path)

    @classmethod
    def _load(cls, path: Path) -> dict[str, ReviewedEncounterAddActivityPlan]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported reviewed encounter add activity schema_version")
        encounters = payload.get("encounters")
        if not isinstance(encounters, list):
            raise ValueError("reviewed encounter add activity encounters must be a list")
        plans: dict[str, ReviewedEncounterAddActivityPlan] = {}
        for raw in encounters:
            if not isinstance(raw, dict):
                raise ValueError("reviewed encounter add activity encounter rows must be objects")
            actor_rows = raw.get("actors")
            if not isinstance(actor_rows, list):
                raise ValueError("reviewed encounter add activity actors must be a list")
            actors = []
            for actor in actor_rows:
                if not isinstance(actor, dict):
                    raise ValueError("reviewed encounter add activity actor rows must be objects")
                coverage = actor.get("signal_coverage") or {}
                actors.append(
                    ReviewedEncounterAddActivityActor(
                        actor_name=str(actor.get("actor_name") or ""),
                        activity_boundary=str(actor.get("activity_boundary") or ""),
                        observed_instances=int(actor.get("observed_instances") or 0),
                        involving_coverage=int(coverage.get("involving") or 0),
                        source_coverage=int(coverage.get("source") or 0),
                        cast_coverage=int(coverage.get("cast") or 0),
                        interpretation=str(actor.get("interpretation") or ""),
                    )
                )
            plan = ReviewedEncounterAddActivityPlan(
                encounter_id=str(raw.get("encounter_id") or ""),
                source=str(raw.get("source") or ""),
                actors=tuple(actors),
            )
            key = plan.encounter_id.casefold()
            if key in plans:
                raise ValueError(
                    f"reviewed encounter add activity cannot duplicate encounter_id {plan.encounter_id!r}"
                )
            plans[key] = plan
        return plans

    def reviewed_for(self, encounter_id: str) -> ReviewedEncounterAddActivityPlan | None:
        key = str(encounter_id or "").strip().casefold()
        if not key:
            raise ValueError("reviewed encounter add activity lookup requires encounter_id")
        return self._plans.get(key)


__all__ = [
    "ReviewedEncounterAddActivityActor",
    "ReviewedEncounterAddActivityPlan",
    "RotationTankEncounterAddActivityService",
]
