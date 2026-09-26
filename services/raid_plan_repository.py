from __future__ import annotations

"""Durable persistence for RaidPlan snapshots.

RaidPlan owns trial-specific planning decisions. This repository persists only that
planning snapshot; it never creates or mutates Personnel, Character, Saved Build, Team,
or canonical encounter identity.
"""

from dataclasses import asdict, replace
import json
import os
import sqlite3
from pathlib import Path
from tempfile import NamedTemporaryFile

from models.raid_plan import (
    RaidPlan,
    RaidPlanCoverageProvider,
    RaidPlanMember,
    RaidPlanTriggeredResponsibility,
)
from services.roster_placeholder_identity import is_personnel_placeholder
from services.raid_plan_pydantic_schema import ValidationError, validate_raid_plan_payload


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


class RaidPlanConflictError(RaidPlanRepositoryError):
    """The plan changed since the editor loaded its saved snapshot."""


def duplicate_occupied_player_seats(plan: RaidPlan) -> tuple[str, ...]:
    """Find one real player assigned to multiple raid seats before a UI save."""
    by_name: dict[str, list[str]] = {}
    by_id: dict[str, list[str]] = {}
    for member in plan.members:
        name = " ".join(str(member.gamertag or "").split())
        if not name or name.casefold() in {"recruit", "open"} or is_personnel_placeholder(name):
            continue
        by_name.setdefault(name.casefold(), []).append(member.seat_id)
        player_id = str(member.player_id or "").strip()
        if player_id:
            by_id.setdefault(player_id, []).append(member.seat_id)
    repeated = [
        (name, tuple(seats))
        for name, seats in by_name.items() if len(set(seats)) > 1
    ]
    for player_id, seats in by_id.items():
        if len(set(seats)) > 1 and not any(
            set(seats).issubset(set(group)) for _name, group in repeated
        ):
            repeated.append((player_id, tuple(seats)))
    return tuple(
        f"{label}: {', '.join(seats)}"
        for label, seats in sorted(repeated)
    )


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
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS raid_plan_revision (
                    revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_raid_plan_revision_plan
                ON raid_plan_revision(plan_id, revision_id DESC)
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
        if self._database_mode:
            with self._connect() as db:
                row = db.execute(
                    "SELECT payload_json FROM raid_plan WHERE plan_id = ? COLLATE NOCASE",
                    (wanted,),
                ).fetchone()
            if row is None:
                return None
            try:
                return self._decode_plan(json.loads(str(row["payload_json"])))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise RaidPlanRepositoryError(f"could not read Raid Plan payload: {exc}") from exc
        return next((row for row in self.list_plans() if row.plan_id.casefold() == wanted), None)

    def save(
        self, plan: RaidPlan, *, expected: RaidPlan | None = None,
        must_be_new: bool = False,
        allow_coverage_clear: bool = False,
    ) -> RaidPlan:
        if not isinstance(plan, RaidPlan):
            raise TypeError("plan must be a RaidPlan")
        if self._database_mode:
            payload = json.dumps(self._encode_plan(plan), sort_keys=True)
            with self._connect() as db:
                # Acquire the writer lock before checking the expected snapshot.
                # A second screen cannot slip a write between the check and save.
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute(
                    "SELECT payload_json FROM raid_plan WHERE plan_id = ? COLLATE NOCASE",
                    (plan.plan_id,),
                ).fetchone()
                if must_be_new and existing is not None:
                    raise RaidPlanConflictError(
                        "A Raid Plan with this identity already exists. Reload it or use another plan name."
                    )

                # Coverage is a Raid-Plan-owned overlay edited on a different screen.
                # Older/stale page models may not carry it. Never let any ordinary
                # Raid Plan save erase that overlay merely because its local plan
                # snapshot has an empty/default collection. Explicit Coverage removal
                # must opt in with allow_coverage_clear=True.
                existing_plan = None
                if existing is not None:
                    existing_plan = self._decode_plan(json.loads(str(existing["payload_json"])))
                    if (
                        not allow_coverage_clear
                        and existing_plan.coverage_providers
                        and not plan.coverage_providers
                    ):
                        plan = replace(
                            plan,
                            coverage_providers=existing_plan.coverage_providers,
                        )
                        payload = json.dumps(self._encode_plan(plan), sort_keys=True)

                if expected is not None:
                    if expected.plan_id.casefold() != plan.plan_id.casefold():
                        raise RaidPlanConflictError("saved Raid Plan identity changed")
                    if existing is None or self._decode_plan(
                        json.loads(str(existing["payload_json"]))
                    ) != expected:
                        raise RaidPlanConflictError(
                            "This Raid Plan changed on another screen. Your edits remain here; "
                            "reload or export a backup before saving again."
                        )
                if existing is not None and str(existing["payload_json"]) == payload:
                    return plan
                if existing is not None:
                    previous = str(existing["payload_json"] or "")
                    if previous and previous != payload:
                        db.execute(
                            """
                            INSERT INTO raid_plan_revision(plan_id, payload_json)
                            VALUES (?, ?)
                            """,
                            (plan.plan_id, previous),
                        )
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
                persisted_row = db.execute(
                    "SELECT payload_json FROM raid_plan WHERE plan_id = ? COLLATE NOCASE",
                    (plan.plan_id,),
                ).fetchone()
                if persisted_row is None:
                    raise RaidPlanRepositoryError(
                        f"saved plan {plan.plan_id!r} could not be read back"
                    )
                try:
                    persisted = self._decode_plan(
                        json.loads(str(persisted_row["payload_json"] or ""))
                    )
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise RaidPlanRepositoryError(
                        f"saved plan {plan.plan_id!r} failed read-back validation: {exc}"
                    ) from exc
                if persisted != plan:
                    raise RaidPlanRepositoryError(
                        "saved Raid Plan did not round-trip exactly"
                    )
                db.execute(
                    """
                    DELETE FROM raid_plan_revision
                    WHERE revision_id IN (
                        SELECT revision_id
                        FROM raid_plan_revision
                        WHERE plan_id = ? COLLATE NOCASE
                        ORDER BY revision_id DESC
                        LIMIT -1 OFFSET 50
                    )
                    """,
                    (plan.plan_id,),
                )
            return plan
        plans = list(self.list_plans())
        prior_plan = next(
            (row for row in plans if row.plan_id.casefold() == plan.plan_id.casefold()),
            None,
        )
        if (
            not allow_coverage_clear
            and prior_plan is not None
            and prior_plan.coverage_providers
            and not plan.coverage_providers
        ):
            plan = replace(plan, coverage_providers=prior_plan.coverage_providers)
        if must_be_new and any(
            row.plan_id.casefold() == plan.plan_id.casefold() for row in plans
        ):
            raise RaidPlanConflictError(
                "A Raid Plan with this identity already exists. Reload it or use another plan name."
            )
        if expected is not None:
            prior = next(
                (row for row in plans if row.plan_id.casefold() == plan.plan_id.casefold()),
                None,
            )
            if expected.plan_id.casefold() != plan.plan_id.casefold() or prior != expected:
                raise RaidPlanConflictError(
                    "This Raid Plan changed on another screen. Your edits remain here; "
                    "reload or export a backup before saving again."
                )
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
            normalized_input = dict(raw)
            for collection_name in ("members", "triggered_responsibilities", "coverage_providers"):
                rows = normalized_input.get(collection_name, [])
                if isinstance(rows, list):
                    normalized_input[collection_name] = [
                        {
                            **dict(row),
                            "seat_id": _canonical_seat_id(dict(row).get("seat_id", "")),
                        }
                        if isinstance(row, dict) else row
                        for row in rows
                    ]
            raw = validate_raid_plan_payload(normalized_input)
            members_raw = raw.get("members", [])
            triggered_raw = raw.get("triggered_responsibilities", [])
            coverage_raw = raw.get("coverage_providers", [])
            if not isinstance(members_raw, (list, tuple)) or not isinstance(triggered_raw, (list, tuple)) or not isinstance(coverage_raw, (list, tuple)):
                raise RaidPlanRepositoryError(
                    "persisted Raid Plan members, triggered responsibilities, and coverage providers must be sequences"
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
            coverage_providers = tuple(
                RaidPlanCoverageProvider(
                    **{
                        **dict(row),
                        "seat_id": _canonical_seat_id(dict(row).get("seat_id", "")),
                    }
                )
                for row in coverage_raw
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
                coverage_providers=coverage_providers,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            if isinstance(exc, RaidPlanRepositoryError):
                raise
            raise RaidPlanRepositoryError(f"invalid persisted Raid Plan: {exc}") from exc

    @staticmethod
    def _encode_plan(plan: RaidPlan) -> dict:
        try:
            return validate_raid_plan_payload(asdict(plan))
        except ValidationError as exc:
            raise RaidPlanRepositoryError(f"Raid Plan failed Pydantic save validation: {exc}") from exc

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


__all__ = [
    "RaidPlanRepository", "RaidPlanRepositoryError", "RaidPlanConflictError",
    "duplicate_occupied_player_seats",
]
