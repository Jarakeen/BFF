from __future__ import annotations

"""Read reviewed empirical Tank add-taunt behavior without promoting it to mechanic truth.

This service owns observational strategy evidence mined from ESO Logs. It is explicitly
separate from hard encounter timing and taunt-maintenance policy because one report and
one player's behavior cannot prove universal encounter requirements or continuous aggro
ownership.
"""

from dataclasses import dataclass
import json
from pathlib import Path

from services.paths import DATA


_DEFAULT_PATH = DATA / "encounter_add_taunt_behavior" / "reviewed.json"


@dataclass(frozen=True)
class EmpiricalTimingSummary:
    samples: int
    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float

    def __post_init__(self) -> None:
        if self.samples <= 0:
            raise ValueError("empirical timing summary samples must be positive")
        if self.minimum_seconds < 0:
            raise ValueError("empirical timing summary minimum must be non-negative")
        if not self.minimum_seconds <= self.median_seconds <= self.maximum_seconds:
            raise ValueError("empirical timing summary must satisfy minimum <= median <= maximum")


@dataclass(frozen=True)
class ReviewedAddTauntBehaviorActor:
    actor_name: str
    observed_instances: int
    taunted_instances: int
    untaunted_instances: int
    acquisition_lag: EmpiricalTimingSummary
    repeat_taunt_interval: EmpiricalTimingSummary
    candidate_ranking_context: bool
    hard_timing_policy: bool
    continuous_ownership_proven: bool

    def __post_init__(self) -> None:
        actor_name = str(self.actor_name or "").strip()
        if not actor_name:
            raise ValueError("empirical add taunt actor_name must be non-empty")
        if self.observed_instances <= 0:
            raise ValueError("empirical add taunt observed_instances must be positive")
        if self.taunted_instances < 0 or self.untaunted_instances < 0:
            raise ValueError("empirical add taunt instance counts must be non-negative")
        if self.taunted_instances + self.untaunted_instances != self.observed_instances:
            raise ValueError("empirical add taunt instance counts must account for every observed instance")
        if self.acquisition_lag.samples != self.taunted_instances:
            raise ValueError("empirical acquisition samples must match taunted instance count")
        if self.hard_timing_policy:
            raise ValueError("single-report empirical add taunt behavior cannot be hard timing policy")
        if self.continuous_ownership_proven:
            raise ValueError("single-report empirical add taunt behavior cannot prove continuous ownership")
        object.__setattr__(self, "actor_name", actor_name)

    @property
    def taunt_coverage_fraction(self) -> float:
        return self.taunted_instances / self.observed_instances


@dataclass(frozen=True)
class ReviewedEncounterAddTauntBehavior:
    encounter_id: str
    evidence_scope: str
    source_report: str
    observed_taunt_sources: tuple[str, ...]
    interpretation: str
    actors: tuple[ReviewedAddTauntBehaviorActor, ...]

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        evidence_scope = str(self.evidence_scope or "").strip()
        source_report = str(self.source_report or "").strip()
        interpretation = str(self.interpretation or "").strip()
        if not all((encounter_id, evidence_scope, source_report, interpretation)):
            raise ValueError("empirical add taunt encounter fields must be non-empty")
        if evidence_scope != "single_report_empirical_strategy":
            raise ValueError(f"unsupported empirical add taunt evidence_scope: {evidence_scope!r}")
        sources = tuple(dict.fromkeys(str(value or "").strip() for value in self.observed_taunt_sources))
        if not sources or any(not value for value in sources):
            raise ValueError("empirical add taunt observed_taunt_sources must be non-empty")
        actors = tuple(self.actors)
        if not actors:
            raise ValueError("empirical add taunt encounter requires actors")
        keys = [row.actor_name.casefold() for row in actors]
        if len(keys) != len(set(keys)):
            raise ValueError("empirical add taunt encounter cannot duplicate actor_name")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "evidence_scope", evidence_scope)
        object.__setattr__(self, "source_report", source_report)
        object.__setattr__(self, "observed_taunt_sources", sources)
        object.__setattr__(self, "interpretation", interpretation)
        object.__setattr__(self, "actors", actors)

    def actor(self, actor_name: str) -> ReviewedAddTauntBehaviorActor | None:
        key = str(actor_name or "").strip().casefold()
        for row in self.actors:
            if row.actor_name.casefold() == key:
                return row
        return None


class RotationTankEncounterAddTauntBehaviorService:
    def __init__(self, path: str | Path = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._plans = self._load(self.path)

    @staticmethod
    def _timing(raw: dict, key: str) -> EmpiricalTimingSummary:
        value = raw.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"empirical add taunt {key} must be an object")
        return EmpiricalTimingSummary(
            samples=int(value.get("samples") or 0),
            median_seconds=float(value.get("median") or 0.0),
            minimum_seconds=float(value.get("minimum") or 0.0),
            maximum_seconds=float(value.get("maximum") or 0.0),
        )

    @classmethod
    def _load(cls, path: Path) -> dict[str, ReviewedEncounterAddTauntBehavior]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported empirical add taunt behavior schema_version")
        encounter_rows = payload.get("encounters")
        if not isinstance(encounter_rows, list):
            raise ValueError("empirical add taunt encounters must be a list")
        plans: dict[str, ReviewedEncounterAddTauntBehavior] = {}
        for raw in encounter_rows:
            if not isinstance(raw, dict):
                raise ValueError("empirical add taunt encounter rows must be objects")
            actor_rows = raw.get("actors")
            if not isinstance(actor_rows, list):
                raise ValueError("empirical add taunt actors must be a list")
            actors = tuple(
                ReviewedAddTauntBehaviorActor(
                    actor_name=str(actor.get("actor_name") or ""),
                    observed_instances=int(actor.get("observed_instances") or 0),
                    taunted_instances=int(actor.get("taunted_instances") or 0),
                    untaunted_instances=int(actor.get("untaunted_instances") or 0),
                    acquisition_lag=cls._timing(actor, "acquisition_lag_seconds"),
                    repeat_taunt_interval=cls._timing(actor, "repeat_taunt_interval_seconds"),
                    candidate_ranking_context=bool(actor.get("candidate_ranking_context")),
                    hard_timing_policy=bool(actor.get("hard_timing_policy")),
                    continuous_ownership_proven=bool(actor.get("continuous_ownership_proven")),
                )
                for actor in actor_rows
            )
            plan = ReviewedEncounterAddTauntBehavior(
                encounter_id=str(raw.get("encounter_id") or ""),
                evidence_scope=str(raw.get("evidence_scope") or ""),
                source_report=str(raw.get("source_report") or ""),
                observed_taunt_sources=tuple(raw.get("observed_taunt_sources") or ()),
                interpretation=str(raw.get("interpretation") or ""),
                actors=actors,
            )
            key = plan.encounter_id.casefold()
            if key in plans:
                raise ValueError(f"empirical add taunt behavior cannot duplicate encounter_id {plan.encounter_id!r}")
            plans[key] = plan
        return plans

    def reviewed_for(self, encounter_id: str) -> ReviewedEncounterAddTauntBehavior | None:
        key = str(encounter_id or "").strip().casefold()
        if not key:
            raise ValueError("empirical add taunt behavior lookup requires encounter_id")
        return self._plans.get(key)


__all__ = [
    "EmpiricalTimingSummary",
    "ReviewedAddTauntBehaviorActor",
    "ReviewedEncounterAddTauntBehavior",
    "RotationTankEncounterAddTauntBehaviorService",
]
