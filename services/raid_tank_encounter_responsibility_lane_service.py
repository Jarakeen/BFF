from __future__ import annotations

"""Reviewed encounter-specific Tank responsibility lanes.

This layer describes what distinct Tank responsibility lanes exist for an encounter.
It deliberately does not assign players to those lanes. Provider assignment remains a
separate step so roster order, role labels, or arbitrary tie-breaks never become hidden
strategy truth.

A lane may declare exact Team Optimization prescription slot names when that mapping is
itself reviewed strategy. This is not a generic Main/Off Tank inference: callers may
only bind a prescription slot through an explicit reviewed slot identity stored here.
"""

from dataclasses import dataclass
import json
from pathlib import Path

from services.paths import DATA


_DEFAULT_PATH = DATA / "raid_tank_encounter_responsibility" / "reviewed.json"


@dataclass(frozen=True)
class RaidTankEncounterResponsibility:
    responsibility_id: str
    target_key: str
    action_type: str
    source: str
    required_capability_type: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("responsibility_id", "target_key", "action_type", "source"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"Tank encounter responsibility {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        if self.required_capability_type is not None:
            value = str(self.required_capability_type or "").strip().casefold()
            if not value:
                raise ValueError(
                    "Tank encounter responsibility required_capability_type must be non-empty when supplied"
                )
            object.__setattr__(self, "required_capability_type", value)


@dataclass(frozen=True)
class RaidTankEncounterResponsibilityLane:
    lane_id: str
    display_name: str
    responsibilities: tuple[RaidTankEncounterResponsibility, ...]
    distinct_from: tuple[str, ...] = ()
    prescription_slot_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        lane_id = str(self.lane_id or "").strip()
        display_name = str(self.display_name or "").strip()
        if not lane_id:
            raise ValueError("Tank encounter responsibility lane_id must be non-empty")
        if not display_name:
            raise ValueError("Tank encounter responsibility display_name must be non-empty")
        responsibilities = tuple(self.responsibilities)
        if not responsibilities:
            raise ValueError("Tank encounter responsibility lane requires at least one responsibility")
        ids = [row.responsibility_id for row in responsibilities]
        if len(ids) != len(set(ids)):
            raise ValueError("Tank encounter responsibility lane cannot duplicate responsibility_id")
        distinct_from = tuple(dict.fromkeys(str(value or "").strip() for value in self.distinct_from))
        if any(not value for value in distinct_from):
            raise ValueError("Tank encounter responsibility distinct_from values must be non-empty")
        if lane_id in distinct_from:
            raise ValueError("Tank encounter responsibility lane cannot be distinct from itself")
        slot_names = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in self.prescription_slot_names
            )
        )
        if any(not value for value in slot_names):
            raise ValueError("Tank encounter responsibility prescription_slot_names must be non-empty")
        object.__setattr__(self, "lane_id", lane_id)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "responsibilities", responsibilities)
        object.__setattr__(self, "distinct_from", distinct_from)
        object.__setattr__(self, "prescription_slot_names", slot_names)


@dataclass(frozen=True)
class RaidTankEncounterResponsibilityPlan:
    encounter_id: str
    source: str
    lanes: tuple[RaidTankEncounterResponsibilityLane, ...]

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        source = str(self.source or "").strip()
        if not encounter_id:
            raise ValueError("Tank encounter responsibility plan encounter_id must be non-empty")
        if not source:
            raise ValueError("Tank encounter responsibility plan source must be non-empty")
        lanes = tuple(self.lanes)
        if not lanes:
            raise ValueError("Tank encounter responsibility plan requires at least one lane")
        lane_ids = [lane.lane_id for lane in lanes]
        if len(lane_ids) != len(set(lane_ids)):
            raise ValueError("Tank encounter responsibility plan cannot duplicate lane_id")
        known = set(lane_ids)
        slot_owner: dict[str, str] = {}
        for lane in lanes:
            unknown = tuple(value for value in lane.distinct_from if value not in known)
            if unknown:
                raise ValueError(
                    f"Tank encounter responsibility lane {lane.lane_id!r} references unknown distinct lane(s): {', '.join(unknown)}"
                )
            for other_id in lane.distinct_from:
                other = next(row for row in lanes if row.lane_id == other_id)
                if lane.lane_id not in other.distinct_from:
                    raise ValueError(
                        "Tank encounter responsibility distinctness must be symmetric: "
                        f"{lane.lane_id!r} / {other_id!r}"
                    )
            for slot_name in lane.prescription_slot_names:
                key = slot_name.casefold()
                prior = slot_owner.get(key)
                if prior is not None and prior != lane.lane_id:
                    raise ValueError(
                        "Tank encounter responsibility prescription slot cannot map to multiple lanes: "
                        f"{slot_name!r} -> {prior!r}, {lane.lane_id!r}"
                    )
                slot_owner[key] = lane.lane_id
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "lanes", lanes)

    def lane(self, lane_id: str) -> RaidTankEncounterResponsibilityLane | None:
        key = str(lane_id or "").strip().casefold()
        for lane in self.lanes:
            if lane.lane_id.casefold() == key:
                return lane
        return None

    def lane_for_prescription_slot(
        self,
        slot_name: str,
    ) -> RaidTankEncounterResponsibilityLane | None:
        key = str(slot_name or "").strip().casefold()
        if not key:
            raise ValueError("Tank encounter responsibility prescription slot lookup requires slot_name")
        matches = tuple(
            lane
            for lane in self.lanes
            if any(value.casefold() == key for value in lane.prescription_slot_names)
        )
        if len(matches) > 1:
            raise ValueError(
                "reviewed Tank responsibility prescription slot mapping is ambiguous: "
                + str(slot_name)
            )
        return matches[0] if matches else None


class RaidTankEncounterResponsibilityLaneService:
    """Read reviewed encounter-specific Tank responsibility lanes."""

    def __init__(self, path: str | Path = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._plans = self._load(self.path)

    @staticmethod
    def _required_text(raw: dict, key: str) -> str:
        value = str(raw.get(key) or "").strip()
        if not value:
            raise ValueError(f"Tank encounter responsibility {key} must be non-empty")
        return value

    @classmethod
    def _load(cls, path: Path) -> dict[str, RaidTankEncounterResponsibilityPlan]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported Tank encounter responsibility schema_version")
        encounters = payload.get("encounters")
        if not isinstance(encounters, list):
            raise ValueError("Tank encounter responsibility encounters must be a list")
        plans: dict[str, RaidTankEncounterResponsibilityPlan] = {}
        for raw in encounters:
            if not isinstance(raw, dict):
                raise ValueError("Tank encounter responsibility encounter rows must be objects")
            lane_rows = raw.get("lanes")
            if not isinstance(lane_rows, list):
                raise ValueError("Tank encounter responsibility lanes must be a list")
            lanes = []
            for lane_raw in lane_rows:
                if not isinstance(lane_raw, dict):
                    raise ValueError("Tank encounter responsibility lane rows must be objects")
                responsibility_rows = lane_raw.get("responsibilities")
                if not isinstance(responsibility_rows, list):
                    raise ValueError("Tank encounter responsibility responsibilities must be a list")
                responsibilities = tuple(
                    RaidTankEncounterResponsibility(
                        responsibility_id=cls._required_text(row, "responsibility_id"),
                        target_key=cls._required_text(row, "target_key"),
                        action_type=cls._required_text(row, "action_type"),
                        required_capability_type=(
                            None
                            if row.get("required_capability_type") is None
                            else cls._required_text(row, "required_capability_type")
                        ),
                        source=cls._required_text(row, "source"),
                    )
                    for row in responsibility_rows
                )
                lanes.append(
                    RaidTankEncounterResponsibilityLane(
                        lane_id=cls._required_text(lane_raw, "lane_id"),
                        display_name=cls._required_text(lane_raw, "display_name"),
                        distinct_from=tuple(lane_raw.get("distinct_from") or ()),
                        prescription_slot_names=tuple(
                            lane_raw.get("prescription_slot_names") or ()
                        ),
                        responsibilities=responsibilities,
                    )
                )
            plan = RaidTankEncounterResponsibilityPlan(
                encounter_id=cls._required_text(raw, "encounter_id"),
                source=cls._required_text(raw, "source"),
                lanes=tuple(lanes),
            )
            key = plan.encounter_id.casefold()
            if key in plans:
                raise ValueError(
                    f"Tank encounter responsibility registry cannot duplicate encounter_id {plan.encounter_id!r}"
                )
            plans[key] = plan
        return plans

    def for_encounter(self, encounter_id: str) -> RaidTankEncounterResponsibilityPlan | None:
        key = str(encounter_id or "").strip().casefold()
        if not key:
            raise ValueError("Tank encounter responsibility lookup requires encounter_id")
        return self._plans.get(key)


__all__ = [
    "RaidTankEncounterResponsibility",
    "RaidTankEncounterResponsibilityLane",
    "RaidTankEncounterResponsibilityLaneService",
    "RaidTankEncounterResponsibilityPlan",
]
