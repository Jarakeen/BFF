from __future__ import annotations

"""Normalize and persist ESO Logs ``playerDetails`` evidence.

ESO Logs has exposed player details in more than one shape over time: grouped role
buckets, flat actor lists, JSON-encoded scalar payloads, and probe-style wrapper
objects. This service owns that shape normalization so role evidence is not silently
lost merely because one importer expected a single representation.
"""

from dataclasses import dataclass
import json
import sqlite3
from typing import Any, Callable

from services.esologs_combat_importer import PLAYER_QUERY


QueryProvider = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class EsoLogsNormalizedPlayer:
    role: str
    actor: dict[str, Any]


def _scalar(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _canonical_role(value: Any) -> str:
    raw = str(value or "").strip().casefold()
    if raw in {"healer", "healing", "healers"}:
        return "healer"
    if raw in {"tank", "tanks"}:
        return "tank"
    if raw in {"dps", "damage", "damage_dealer", "dd"}:
        return "dps"
    return raw or "unknown"


def normalize_player_details(value: Any) -> tuple[EsoLogsNormalizedPlayer, ...]:
    """Return player rows from grouped, wrapped, flat, or JSON-scalar shapes."""

    value = _scalar(value)

    # Probe captures and some API wrappers may retain one or both of these layers.
    for _ in range(3):
        if not isinstance(value, dict):
            break
        if "playerDetails" in value:
            value = _scalar(value.get("playerDetails"))
            continue
        if "data" in value and not any(key in value for key in ("healers", "tanks", "dps")):
            value = _scalar(value.get("data"))
            continue
        break

    rows: list[EsoLogsNormalizedPlayer] = []
    if isinstance(value, dict):
        for role_key, role_name in (("healers", "healer"), ("tanks", "tank"), ("dps", "dps")):
            actors = value.get(role_key) or []
            if isinstance(actors, dict):
                actors = list(actors.values())
            if not isinstance(actors, list):
                continue
            for actor in actors:
                if isinstance(actor, dict):
                    rows.append(EsoLogsNormalizedPlayer(role_name, actor))
        return tuple(rows)

    if isinstance(value, list):
        for actor in value:
            if not isinstance(actor, dict):
                continue
            raw_role = actor.get("role") or actor.get("roleName") or actor.get("specRole")
            rows.append(EsoLogsNormalizedPlayer(_canonical_role(raw_role), actor))
    return tuple(rows)


class EsoLogsPlayerDetailsImportService:
    """Fetch and persist fight-scoped ESO Logs player role evidence."""

    def __init__(self, connection: sqlite3.Connection, query_provider: QueryProvider) -> None:
        self.connection = connection
        self.query_provider = query_provider

    def import_fight(self, *, report_code: str, fight: dict[str, Any]) -> int:
        fight_id = int(fight["id"])
        response = self.query_provider(
            PLAYER_QUERY,
            {
                "code": report_code,
                "fightIDs": [fight_id],
                "startTime": float(fight["startTime"]),
                "endTime": float(fight["endTime"]),
            },
        )
        report = (response.get("reportData") or {}).get("report") or {}
        rows = normalize_player_details(report.get("playerDetails"))

        self.connection.execute(
            "DELETE FROM log_actor WHERE report_code = ? AND fight_id = ?",
            (report_code, fight_id),
        )
        count = 0
        for row in rows:
            actor = row.actor
            actor_id = actor.get("id")
            if actor_id is None:
                continue
            actor_id = int(actor_id)
            if actor_id < 0:
                continue
            self.connection.execute(
                """
                INSERT INTO log_actor (
                    report_code, fight_id, actor_id, guid, name, display_name,
                    actor_type, role, anonymous, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_code,
                    fight_id,
                    actor_id,
                    actor.get("guid"),
                    actor.get("name"),
                    actor.get("displayName"),
                    actor.get("type"),
                    row.role,
                    int(bool(actor.get("anonymous"))),
                    json.dumps(actor, ensure_ascii=False, sort_keys=True),
                ),
            )
            count += 1
        self.connection.commit()
        return count

    def import_fights(self, *, report_code: str, fights: tuple[dict[str, Any], ...]) -> int:
        return sum(self.import_fight(report_code=report_code, fight=fight) for fight in fights)


__all__ = [
    "EsoLogsNormalizedPlayer",
    "EsoLogsPlayerDetailsImportService",
    "normalize_player_details",
]
