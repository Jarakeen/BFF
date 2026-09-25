from __future__ import annotations

"""Restore one Raid Plan from its durable revision history.

This is deliberately surgical: it restores one raid_plan payload through the
canonical RaidPlanRepository and leaves every other user-owned table untouched.
A full foundrydock.db safety snapshot is created immediately before an applied
restore.
"""

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from engine.config import get_user_database_path
from services.raid_plan_repository import RaidPlanRepository
from services.user_safety_snapshot_service import UserSafetySnapshotService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


@dataclass(frozen=True)
class RevisionCandidate:
    plan_id: str
    name: str
    source: str
    ordinal: int
    timestamp: str
    payload: dict

    @property
    def members(self) -> tuple[dict, ...]:
        rows = self.payload.get("members", [])
        return tuple(row for row in rows if isinstance(row, dict))


def _member_name(member: dict) -> str:
    return _clean(
        member.get("gamertag")
        or member.get("player_name")
        or member.get("character_name")
    )


def _plan_matches(candidate: RevisionCandidate, plan_hint: str) -> bool:
    hint = _key(plan_hint)
    if not hint:
        return True
    haystack = " ".join(
        (
            candidate.plan_id,
            candidate.name,
            _clean(candidate.payload.get("team_name")),
            _clean(candidate.payload.get("trial_id")),
        )
    ).casefold()
    return hint in haystack


def _tank_matches(candidate: RevisionCandidate, tank_name: str) -> bool:
    wanted = _key(tank_name)
    if not wanted:
        return True
    for member in candidate.members:
        seat = _key(member.get("seat_id"))
        if seat not in {"tank-1", "tank-2", "main-tank", "off-tank"}:
            continue
        if wanted in _key(_member_name(member)):
            return True
    return False


def _count_player(candidate: RevisionCandidate, player_name: str) -> int:
    wanted = _key(player_name)
    if not wanted:
        return 0
    return sum(
        1
        for member in candidate.members
        if wanted in _key(_member_name(member))
    )


def _read_candidates(database_path: Path) -> tuple[RevisionCandidate, ...]:
    if not database_path.is_file():
        raise FileNotFoundError(f"FoundryDock database not found: {database_path}")

    rows: list[RevisionCandidate] = []
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        current = db.execute(
            """
            SELECT plan_id, payload_json, updated_at
            FROM raid_plan
            ORDER BY updated_at DESC, plan_id COLLATE NOCASE
            """
        ).fetchall()
        for row in current:
            try:
                payload = json.loads(str(row["payload_json"] or ""))
            except json.JSONDecodeError:
                continue
            rows.append(
                RevisionCandidate(
                    plan_id=str(row["plan_id"] or ""),
                    name=_clean(payload.get("name")),
                    source="current",
                    ordinal=0,
                    timestamp=str(row["updated_at"] or ""),
                    payload=payload,
                )
            )

        revisions = db.execute(
            """
            SELECT revision_id, plan_id, payload_json, saved_at
            FROM raid_plan_revision
            ORDER BY revision_id DESC
            """
        ).fetchall()
        for row in revisions:
            try:
                payload = json.loads(str(row["payload_json"] or ""))
            except json.JSONDecodeError:
                continue
            rows.append(
                RevisionCandidate(
                    plan_id=str(row["plan_id"] or ""),
                    name=_clean(payload.get("name")),
                    source="revision",
                    ordinal=int(row["revision_id"] or 0),
                    timestamp=str(row["saved_at"] or ""),
                    payload=payload,
                )
            )
    return tuple(rows)


def _timestamp_value(value: str) -> datetime | None:
    text = _clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def find_recovery_candidates(
    database_path: Path,
    *,
    plan_hint: str,
    tank_name: str,
    unique_player: str,
) -> tuple[RevisionCandidate, ...]:
    candidates = _read_candidates(database_path)
    return tuple(
        row
        for row in candidates
        if row.source == "revision"
        and _plan_matches(row, plan_hint)
        and _tank_matches(row, tank_name)
        and _count_player(row, unique_player) <= 1
    )


def find_recovery_candidate(
    database_path: Path,
    *,
    plan_hint: str,
    tank_name: str,
    unique_player: str,
    target_age_minutes: int | None = None,
    now: datetime | None = None,
) -> RevisionCandidate | None:
    matches = list(
        find_recovery_candidates(
            database_path,
            plan_hint=plan_hint,
            tank_name=tank_name,
            unique_player=unique_player,
        )
    )
    if not matches:
        return None

    if target_age_minutes is None:
        return matches[0]

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    target = current.astimezone(timezone.utc).timestamp() - (int(target_age_minutes) * 60)

    def distance(row: RevisionCandidate) -> tuple[float, int]:
        stamp = _timestamp_value(row.timestamp)
        if stamp is None:
            return (float("inf"), -row.ordinal)
        return (abs(stamp.timestamp() - target), -row.ordinal)

    return min(matches, key=distance)


def _seat_summary(candidate: RevisionCandidate) -> str:
    lines = []
    for member in candidate.members:
        seat = _clean(member.get("seat_id")) or "?"
        name = _member_name(member) or "(open)"
        character = _clean(member.get("character_name"))
        suffix = f" / {character}" if character and character.casefold() != name.casefold() else ""
        lines.append(f"  {seat}: {name}{suffix}")
    return "\n".join(lines) if lines else "  (no members)"


def restore_candidate(database_path: Path, candidate: RevisionCandidate) -> Path | None:
    snapshot = UserSafetySnapshotService(database_path=database_path).create(
        f"before-raid-plan-revision-restore-{candidate.plan_id}"
    )
    repository = RaidPlanRepository(database_path)
    plan = repository._decode_plan(candidate.payload)
    repository.save(plan)
    persisted = repository.get(plan.plan_id)
    if persisted != plan:
        raise RuntimeError("Restored Raid Plan failed canonical read-back verification.")
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore the newest Raid Plan revision matching known-good roster conditions."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=get_user_database_path(),
        help="Path to foundrydock.db. Defaults to the active FoundryDock user database.",
    )
    parser.add_argument(
        "--plan",
        default="Performance Mode",
        help="Text that must appear in plan id/name/team/trial. Default: Performance Mode",
    )
    parser.add_argument(
        "--tank",
        default="Rik",
        help="Player text that must appear in a Tank seat. Default: Rik",
    )
    parser.add_argument(
        "--unique-player",
        default="Aces",
        help="Player text that may appear in at most one seat. Default: Aces",
    )
    parser.add_argument(
        "--target-age-minutes",
        type=int,
        default=None,
        help="Prefer the matching revision closest to this many minutes ago.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent matching revisions with seat summaries instead of choosing one.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum revisions to show with --list. Default: 10",
    )
    parser.add_argument(
        "--revision-id",
        type=int,
        default=None,
        help="Preview or restore one exact raid_plan_revision revision_id.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually restore the matched revision. Without this flag, only preview it.",
    )
    args = parser.parse_args()

    database = args.database.expanduser().resolve()

    matches = list(
        find_recovery_candidates(
            database,
            plan_hint=args.plan,
            tank_name=args.tank,
            unique_player=args.unique_player,
        )
    )

    if args.list:
        if not matches:
            print(
                "No Raid Plan revisions matched: "
                f"plan~{args.plan!r}, Tank~{args.tank!r}, "
                f"{args.unique_player!r} in <= 1 seat."
            )
            return 2
        for row in matches[: max(1, int(args.limit))]:
            print("=" * 72)
            print(
                f"revision {row.ordinal} | {row.timestamp} | "
                f"{row.name} [{row.plan_id}]"
            )
            print(_seat_summary(row))
        return 0

    if args.revision_id is not None:
        candidate = next(
            (row for row in matches if row.ordinal == int(args.revision_id)),
            None,
        )
    else:
        candidate = find_recovery_candidate(
            database,
            plan_hint=args.plan,
            tank_name=args.tank,
            unique_player=args.unique_player,
            target_age_minutes=args.target_age_minutes,
        )

    if candidate is None:
        label = (
            f"revision_id={args.revision_id}"
            if args.revision_id is not None
            else (
                f"plan~{args.plan!r}, Tank~{args.tank!r}, "
                f"{args.unique_player!r} in <= 1 seat"
            )
        )
        print(f"No Raid Plan revision matched: {label}.")
        return 2

    print(
        f"Matched {candidate.source} {candidate.ordinal or ''} "
        f"from {candidate.timestamp}: {candidate.name} [{candidate.plan_id}]"
    )
    print(_seat_summary(candidate))

    if not args.apply:
        print("\nPreview only. Re-run with --apply to restore this Raid Plan.")
        return 0

    snapshot = restore_candidate(database, candidate)
    print(f"\nRestored Raid Plan: {candidate.name}")
    if snapshot is not None:
        print(f"Safety snapshot: {snapshot}")
    print("Only this Raid Plan was restored. Other user data was left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
