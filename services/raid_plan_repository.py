from __future__ import annotations

"""Durable persistence for RaidPlan snapshots.

RaidPlan owns trial-specific planning decisions. This repository persists only that
planning snapshot; it never creates or mutates Personnel, Character, Saved Build, Team,
or canonical encounter identity.
"""

from dataclasses import asdict
import json
import os
import sqlite3
from pathlib import Path
from tempfile import NamedTemporaryFile

from models.raid_plan import (
    RaidPlan,
    RaidPlanMember,
    RaidPlanTriggeredResponsibility,
)


_SCHEMA_VERSION = 1


_LEGACY_SEAT_IDS = {
    "main-tank": "tank-1",
    "off-tank": "tank-2",
}


def _canonical_seat_id(value: object) -> str:
    seat = str(value or "").strip()
    return _LEGACY_SEAT_IDS.get(seat.casefold(), seat)


class RaidPlanRepositoryError(ValueError):
    """Raised when persisted Raid Plan data cannot be trusted."""


class RaidPlanRepository:
    """Versioned JSON repository keyed by stable RaidPlan.plan_id."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._database_mode = self.path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}
        if self._database_mode:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_database_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_database_schema(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS raid_plan (
                    plan_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def list_plans(self) -> tuple[RaidPlan, ...]:
        if self._database_mode:
            with self._connect() as db:
                rows = db.execute(
                    "SELECT payload_json FROM raid_plan ORDER BY plan_id COLLATE NOCASE"
                ).fetchall()
            raw_rows = []
            for row in rows:
                try:
                    raw_rows.append(json.loads(str(row["payload_json"] or "")))
                except json.JSONDecodeError as exc:
                    raise RaidPlanRepositoryError(
                        f"could not read Raid Plan database payload: {exc}"
                    ) from exc
            plans = tuple(self._decode_plan(row) for row in raw_rows)
        else:
            payload = self._load_payload()
            plans = tuple(self._decode_plan(row) for row in payload["plans"])
        return tuple(sorted(plans, key=lambda row: (row.name.casefold(), row.plan_id.casefold())))

    def get(self, plan_id: str) -> RaidPlan | None:
        wanted = str(plan_id or "").strip().casefold()
        if not wanted:
            return None
        return next((row for row in self.list_plans() if row.plan_id.casefold() == wanted), None)

    def save(self, plan: RaidPlan) -> RaidPlan:
        if not isinstance(plan, RaidPlan):
            raise TypeError("plan must be a RaidPlan")
        if self._database_mode:
            payload = json.dumps(self._encode_plan(plan), sort_keys=True)
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO raid_plan(plan_id, payload_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(plan_id) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (plan.plan_id, payload),
                )
            return plan
        plans = list(self.list_plans())
        wanted = plan.plan_id.casefold()
        replaced = False
        updated: list[RaidPlan] = []
        for existing in plans:
            if existing.plan_id.casefold() == wanted:
                updated.append(plan)
                replaced = True
            else:
                updated.append(existing)
        if not replaced:
            updated.append(plan)
        self._write_plans(tuple(updated))
        return plan

    def delete(self, plan_id: str) -> bool:
        wanted = str(plan_id or "").strip().casefold()
        if not wanted:
            return False
        if self._database_mode:
            with self._connect() as db:
                row = db.execute(
                    "SELECT plan_id FROM raid_plan WHERE plan_id = ? COLLATE NOCASE",
                    (str(plan_id or "").strip(),),
                ).fetchone()
                if row is None:
                    return False
                db.execute("DELETE FROM raid_plan WHERE plan_id = ?", (row["plan_id"],))
            return True
        plans = self.list_plans()
        kept = tuple(row for row in plans if row.plan_id.casefold() != wanted)
        if len(kept) == len(plans):
            return False
        self._write_plans(kept)
        return True

    def _load_payload(self) -> dict:
        if not self.path.exists():
            return {"schema_version": _SCHEMA_VERSION, "plans": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RaidPlanRepositoryError(f"could not read Raid Plan repository: {exc}") from exc
        if not isinstance(raw, dict):
            raise RaidPlanRepositoryError("Raid Plan repository root must be an object")
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise RaidPlanRepositoryError(
                f"unsupported Raid Plan repository schema: {raw.get('schema_version')!r}"
            )
        plans = raw.get("plans")
        if not isinstance(plans, list):
            raise RaidPlanRepositoryError("Raid Plan repository plans must be a list")
        return {"schema_version": _SCHEMA_VERSION, "plans": plans}

    @staticmethod
    def _decode_plan(raw: object) -> RaidPlan:
        if not isinstance(raw, dict):
            raise RaidPlanRepositoryError("persisted Raid Plan must be an object")
        try:
            members_raw = raw.get("members", [])
            triggered_raw = raw.get("triggered_responsibilities", [])
            if not isinstance(members_raw, list) or not isinstance(triggered_raw, list):
                raise RaidPlanRepositoryError(
                    "persisted Raid Plan members and triggered responsibilities must be lists"
                )
            members = tuple(
                RaidPlanMember(
                    **{
                        **dict(row),
                        "seat_id": _canonical_seat_id(dict(row).get("seat_id", "")),
                    }
                )
                for row in members_raw
            )
            triggered = tuple(
                RaidPlanTriggeredResponsibility(
                    **{
                        **dict(row),
                        "seat_id": _canonical_seat_id(dict(row).get("seat_id", "")),
                    }
                )
                for row in triggered_raw
            )
            return RaidPlan(
                plan_id=raw.get("plan_id", ""),
                trial_id=raw.get("trial_id", ""),
                name=raw.get("name", ""),
                team_name=raw.get("team_name"),
                difficulty=raw.get("difficulty"),
                plan_note=raw.get("plan_note"),
                status=raw.get("status", "planning"),
                members=members,
                triggered_responsibilities=triggered,
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, RaidPlanRepositoryError):
                raise
            raise RaidPlanRepositoryError(f"invalid persisted Raid Plan: {exc}") from exc

    @staticmethod
    def _encode_plan(plan: RaidPlan) -> dict:
        return asdict(plan)

    def _write_plans(self, plans: tuple[RaidPlan, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "plans": [self._encode_plan(row) for row in plans],
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        temp_name: str | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
                temp_name = handle.name
            os.replace(temp_name, self.path)
        except OSError as exc:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise RaidPlanRepositoryError(f"could not write Raid Plan repository: {exc}") from exc


__all__ = ["RaidPlanRepository", "RaidPlanRepositoryError"]
