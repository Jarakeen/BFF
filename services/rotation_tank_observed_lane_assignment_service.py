from __future__ import annotations

"""Read reviewed report-scoped Tank lane assignments.

This service records observational assignments from reviewed combat evidence. It does
not infer generic Main Tank / Off Tank identity and does not replace encounter-level
prescription-slot semantics.
"""

from dataclasses import dataclass
import json
from pathlib import Path


_DEFAULT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "encounter_tank_observed_lane_assignment"
    / "reviewed.json"
)


@dataclass(frozen=True)
class ReviewedObservedTankLane:
    lane_id: str
    source_id: int
    character_name: str
    account_name: str
    actor_type: str
    eso_logs_role: str
    role_fights: int
    boss_taunt_events: int
    boss_fights: int
    add_taunt_events: int
    add_instances: int
    interpretation: str

    def __post_init__(self) -> None:
        for field_name in (
            "lane_id",
            "character_name",
            "account_name",
            "actor_type",
            "eso_logs_role",
            "interpretation",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"reviewed observed Tank lane {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        if self.source_id < 0:
            raise ValueError("reviewed observed Tank lane source_id must be non-negative")
        for field_name in (
            "role_fights",
            "boss_taunt_events",
            "boss_fights",
            "add_taunt_events",
            "add_instances",
        ):
            if int(getattr(self, field_name)) < 0:
                raise ValueError(f"reviewed observed Tank lane {field_name} must be non-negative")
        if self.eso_logs_role.casefold() != "tank":
            raise ValueError("reviewed observed Tank lane requires ESO Logs tank role evidence")


@dataclass(frozen=True)
class ReviewedObservedTankLaneAssignment:
    encounter_id: str
    report_code: str
    evidence_scope: str
    taunt_state_effect_id: int
    fights: tuple[int, ...]
    lanes: tuple[ReviewedObservedTankLane, ...]
    interpretation: str

    def lane(self, lane_id: str) -> ReviewedObservedTankLane | None:
        key = str(lane_id or "").strip().casefold()
        if not key:
            raise ValueError("observed Tank lane lookup requires lane_id")
        return next((row for row in self.lanes if row.lane_id.casefold() == key), None)


class RotationTankObservedLaneAssignmentService:
    def __init__(self, path: str | Path = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._assignments = self._load(self.path)

    @classmethod
    def _load(cls, path: Path) -> dict[tuple[str, str], ReviewedObservedTankLaneAssignment]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported observed Tank lane assignment schema_version")
        rows = payload.get("assignments")
        if not isinstance(rows, list):
            raise ValueError("observed Tank lane assignments must be a list")
        result: dict[tuple[str, str], ReviewedObservedTankLaneAssignment] = {}
        for raw in rows:
            lanes = tuple(
                ReviewedObservedTankLane(
                    lane_id=str(item.get("lane_id") or ""),
                    source_id=int(item.get("source_id", -1)),
                    character_name=str(item.get("character_name") or ""),
                    account_name=str(item.get("account_name") or ""),
                    actor_type=str(item.get("actor_type") or ""),
                    eso_logs_role=str(item.get("eso_logs_role") or ""),
                    role_fights=int(item.get("role_fights") or 0),
                    boss_taunt_events=int(item.get("boss_taunt_events") or 0),
                    boss_fights=int(item.get("boss_fights") or 0),
                    add_taunt_events=int(item.get("add_taunt_events") or 0),
                    add_instances=int(item.get("add_instances") or 0),
                    interpretation=str(item.get("interpretation") or ""),
                )
                for item in raw.get("lanes") or ()
            )
            assignment = ReviewedObservedTankLaneAssignment(
                encounter_id=str(raw.get("encounter_id") or "").strip(),
                report_code=str(raw.get("report_code") or "").strip(),
                evidence_scope=str(raw.get("evidence_scope") or "").strip(),
                taunt_state_effect_id=int(raw.get("taunt_state_effect_id") or 0),
                fights=tuple(int(value) for value in raw.get("fights") or ()),
                lanes=lanes,
                interpretation=str(raw.get("interpretation") or "").strip(),
            )
            if not all((assignment.encounter_id, assignment.report_code, assignment.interpretation)):
                raise ValueError("observed Tank lane assignment identifiers must be non-empty")
            if assignment.evidence_scope != "single_report_reviewed_observed_lane_assignment":
                raise ValueError(f"unsupported observed Tank lane evidence_scope: {assignment.evidence_scope!r}")
            if assignment.taunt_state_effect_id <= 0:
                raise ValueError("observed Tank lane assignment requires positive taunt_state_effect_id")
            if not assignment.fights:
                raise ValueError("observed Tank lane assignment requires reviewed fights")
            if len(set(assignment.fights)) != len(assignment.fights):
                raise ValueError("observed Tank lane assignment cannot duplicate fight ids")
            if not assignment.lanes:
                raise ValueError("observed Tank lane assignment requires lanes")
            lane_ids = [lane.lane_id.casefold() for lane in assignment.lanes]
            if len(lane_ids) != len(set(lane_ids)):
                raise ValueError("observed Tank lane assignment cannot duplicate lane ids")
            source_ids = [lane.source_id for lane in assignment.lanes]
            if len(source_ids) != len(set(source_ids)):
                raise ValueError("observed Tank lane assignment cannot map one source to multiple lanes")
            key = (assignment.encounter_id.casefold(), assignment.report_code.casefold())
            if key in result:
                raise ValueError("duplicate observed Tank lane assignment encounter/report pair")
            result[key] = assignment
        return result

    def reviewed_for(
        self,
        *,
        encounter_id: str,
        report_code: str,
    ) -> ReviewedObservedTankLaneAssignment | None:
        encounter = str(encounter_id or "").strip().casefold()
        report = str(report_code or "").strip().casefold()
        if not encounter or not report:
            raise ValueError("observed Tank lane assignment lookup requires encounter_id and report_code")
        return self._assignments.get((encounter, report))


__all__ = [
    "ReviewedObservedTankLane",
    "ReviewedObservedTankLaneAssignment",
    "RotationTankObservedLaneAssignmentService",
]
