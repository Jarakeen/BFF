from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from services.esologs_client import EsoLogsClient


REPORT_URL = "https://www.esologs.com/reports/{report_code}"


PLAYER_QUERY = """
query ImportPlayers(
  $code: String!
  $fightIDs: [Int]
  $startTime: Float
  $endTime: Float
) {
  reportData {
    report(code: $code) {
      playerDetails(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        translate: true
        includeCombatantInfo: true
      )
    }
  }
}
"""

EVENT_QUERY = """
query ImportEvents(
  $code: String!
  $fightIDs: [Int]
  $startTime: Float
  $endTime: Float
  $includeResources: Boolean!
  $limit: Int!
) {
  reportData {
    report(code: $code) {
      events(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        includeResources: $includeResources
        limit: $limit
        translate: true
        useAbilityIDs: true
        useActorIDs: true
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""


class EsoLogsCombatImporter:
    """Import raw ESO Logs combat evidence without prematurely normalizing it."""

    def __init__(self, connection: sqlite3.Connection, client: EsoLogsClient):
        self.connection = connection
        self.client = client
        self.connection.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS log_actor (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                guid INTEGER,
                name TEXT,
                display_name TEXT,
                actor_type TEXT,
                role TEXT,
                anonymous INTEGER,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (report_code, fight_id, actor_id)
            );

            CREATE TABLE IF NOT EXISTS log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source_id INTEGER,
                source_is_friendly INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                target_is_friendly INTEGER,
                ability_game_id INTEGER,
                extra_ability_game_id INTEGER,
                amount REAL,
                hit_type INTEGER,
                tick INTEGER,
                cast_track_id INTEGER,
                resource_change REAL,
                resource_change_type INTEGER,
                other_resource_change REAL,
                max_resource_amount REAL,
                waste REAL,
                overheal REAL,
                absorbed REAL,
                stack INTEGER,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (report_code, fight_id, event_index)
            );

            CREATE INDEX IF NOT EXISTS idx_log_event_fight_time
                ON log_event(report_code, fight_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_log_event_source
                ON log_event(report_code, fight_id, source_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_log_event_target
                ON log_event(report_code, fight_id, target_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_log_event_ability
                ON log_event(report_code, fight_id, ability_game_id, timestamp);

            CREATE TABLE IF NOT EXISTS log_observed_target (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                max_hit_points REAL,
                damage_event_count INTEGER NOT NULL DEFAULT 0,
                damage_amount REAL NOT NULL DEFAULT 0,
                first_damage_time REAL,
                last_damage_time REAL,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (report_code, fight_id, target_id)
            );

            CREATE TABLE IF NOT EXISTS log_observed_damage_window (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                window_index INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration REAL NOT NULL,
                gap_threshold_ms REAL NOT NULL,
                method TEXT NOT NULL,
                PRIMARY KEY (report_code, fight_id, window_index)
            );
            """
        )
        self.connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _scalar(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return self.client._query(query, variables)

    def _fetch_events(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        *,
        include_resources: bool = True,
        limit: int = 10_000,
        max_pages: int = 200,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        page_start = float(start_time)

        for _ in range(max_pages):
            data = self._query(
                EVENT_QUERY,
                {
                    "code": report_code,
                    "fightIDs": [int(fight_id)],
                    "startTime": page_start,
                    "endTime": float(end_time),
                    "includeResources": include_resources,
                    "limit": max(100, min(int(limit), 10_000)),
                },
            )
            report = (data.get("reportData") or {}).get("report") or {}
            page = report.get("events") or {}
            rows = self._scalar(page.get("data")) or []
            if not isinstance(rows, list):
                rows = [rows]
            events.extend(rows)

            next_timestamp = page.get("nextPageTimestamp")
            if not next_timestamp or not rows:
                break
            next_timestamp = float(next_timestamp)
            if next_timestamp <= page_start or next_timestamp >= float(end_time):
                break
            page_start = next_timestamp

        return events

    def _import_actors(self, report_code: str, fight: dict[str, Any]) -> int:
        fight_id = int(fight["id"])
        start = float(fight["startTime"])
        end = float(fight["endTime"])
        data = self._query(
            PLAYER_QUERY,
            {
                "code": report_code,
                "fightIDs": [fight_id],
                "startTime": start,
                "endTime": end,
            },
        )
        report = (data.get("reportData") or {}).get("report") or {}
        player_details = self._scalar(report.get("playerDetails")) or {}

        self.connection.execute(
            "DELETE FROM log_actor WHERE report_code = ? AND fight_id = ?",
            (report_code, fight_id),
        )

        count = 0
        for role_key, role_name in (("healers", "healer"), ("tanks", "tank"), ("dps", "dps")):
            for actor in player_details.get(role_key) or []:
                actor_id = int(actor.get("id", -1))
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
                        role_name,
                        int(bool(actor.get("anonymous"))),
                        self._json(actor),
                    ),
                )
                count += 1
        return count

    def _import_events(self, report_code: str, fight: dict[str, Any]) -> int:
        fight_id = int(fight["id"])
        start = float(fight["startTime"])
        end = float(fight["endTime"])
        events = self._fetch_events(report_code, fight_id, start, end)

        self.connection.execute(
            "DELETE FROM log_event WHERE report_code = ? AND fight_id = ?",
            (report_code, fight_id),
        )

        for index, event in enumerate(events):
            self.connection.execute(
                """
                INSERT INTO log_event (
                    report_code, fight_id, event_index, timestamp, event_type,
                    source_id, source_is_friendly, target_id, target_instance,
                    target_is_friendly, ability_game_id, extra_ability_game_id,
                    amount, hit_type, tick, cast_track_id, resource_change,
                    resource_change_type, other_resource_change, max_resource_amount,
                    waste, overheal, absorbed, stack, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_code,
                    fight_id,
                    index,
                    float(event.get("timestamp", 0)),
                    event.get("type", "unknown"),
                    event.get("sourceID"),
                    None if event.get("sourceIsFriendly") is None else int(bool(event.get("sourceIsFriendly"))),
                    event.get("targetID"),
                    event.get("targetInstance"),
                    None if event.get("targetIsFriendly") is None else int(bool(event.get("targetIsFriendly"))),
                    event.get("abilityGameID"),
                    event.get("extraAbilityGameID"),
                    event.get("amount"),
                    event.get("hitType"),
                    None if event.get("tick") is None else int(bool(event.get("tick"))),
                    event.get("castTrackID"),
                    event.get("resourceChange"),
                    event.get("resourceChangeType"),
                    event.get("otherResourceChange"),
                    event.get("maxResourceAmount"),
                    event.get("waste"),
                    event.get("overheal"),
                    event.get("absorbed"),
                    event.get("stack"),
                    self._json(event),
                ),
            )

        return len(events)

    def _rebuild_observed_windows(self, report_code: str, fight: dict[str, Any], gap_threshold_ms: float = 3000.0) -> int:
        fight_id = int(fight["id"])
        self.connection.execute(
            "DELETE FROM log_observed_target WHERE report_code = ? AND fight_id = ?",
            (report_code, fight_id),
        )
        self.connection.execute(
            "DELETE FROM log_observed_damage_window WHERE report_code = ? AND fight_id = ?",
            (report_code, fight_id),
        )

        rows = self.connection.execute(
            """
            SELECT target_id,
                   COUNT(*) AS damage_event_count,
                   SUM(COALESCE(amount, 0)) AS damage_amount,
                   MIN(timestamp) AS first_damage_time,
                   MAX(timestamp) AS last_damage_time
            FROM log_event
            WHERE report_code = ?
              AND fight_id = ?
              AND event_type = 'damage'
              AND source_is_friendly = 1
              AND target_is_friendly = 0
              AND target_id IS NOT NULL
            GROUP BY target_id
            ORDER BY damage_amount DESC
            """,
            (report_code, fight_id),
        ).fetchall()

        if not rows:
            return 0

        # The main encounter target is the highest-health hostile target that
        # actually received friendly damage. This is an observed heuristic,
        # not a claim that every multi-boss encounter has one true target.
        target_candidates = self.connection.execute(
            """
            SELECT target_id, MAX(COALESCE(json_extract(raw_json, '$.targetResources.maxHitPoints'), 0)) AS max_hp
            FROM log_event
            WHERE report_code = ?
              AND fight_id = ?
              AND event_type = 'damage'
              AND source_is_friendly = 1
              AND target_is_friendly = 0
              AND target_id IS NOT NULL
            GROUP BY target_id
            ORDER BY max_hp DESC
            """,
            (report_code, fight_id),
        ).fetchall()
        target_id = int(target_candidates[0]["target_id"])
        max_hp = float(target_candidates[0]["max_hp"] or 0)

        target_row = next((row for row in rows if int(row["target_id"]) == target_id), None)
        self.connection.execute(
            """
            INSERT INTO log_observed_target (
                report_code, fight_id, target_id, max_hit_points,
                damage_event_count, damage_amount, first_damage_time,
                last_damage_time, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_code,
                fight_id,
                target_id,
                max_hp,
                int(target_row["damage_event_count"]),
                float(target_row["damage_amount"] or 0),
                target_row["first_damage_time"],
                target_row["last_damage_time"],
                self._json({"selection": "highest_hostile_max_hp", "candidate_count": len(target_candidates)}),
            ),
        )

        timestamps = [
            float(row["timestamp"])
            for row in self.connection.execute(
                """
                SELECT timestamp
                FROM log_event
                WHERE report_code = ?
                  AND fight_id = ?
                  AND event_type = 'damage'
                  AND source_is_friendly = 1
                  AND target_id = ?
                ORDER BY timestamp
                """,
                (report_code, fight_id, target_id),
            ).fetchall()
        ]
        if not timestamps:
            return 0

        windows: list[tuple[float, float]] = []
        window_start = previous = timestamps[0]
        for timestamp in timestamps[1:]:
            if timestamp - previous > gap_threshold_ms:
                windows.append((window_start, previous))
                window_start = timestamp
            previous = timestamp
        windows.append((window_start, previous))

        for index, (start, end) in enumerate(windows):
            self.connection.execute(
                """
                INSERT INTO log_observed_damage_window (
                    report_code, fight_id, window_index, target_id,
                    start_time, end_time, duration, gap_threshold_ms, method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_code,
                    fight_id,
                    index,
                    target_id,
                    start,
                    end,
                    end - start,
                    gap_threshold_ms,
                    "friendly_damage_gap_heuristic",
                ),
            )
        return len(windows)

    def import_fight(self, report_code: str, fight: dict[str, Any], gap_threshold_ms: float = 3000.0) -> dict[str, int]:
        actors = self._import_actors(report_code, fight)
        events = self._import_events(report_code, fight)
        windows = self._rebuild_observed_windows(report_code, fight, gap_threshold_ms)
        self.connection.commit()
        return {"actors": actors, "events": events, "observed_windows": windows}

    def import_report(self, report_code: str, fight_ids: list[int] | None = None, gap_threshold_ms: float = 3000.0) -> dict[str, int]:
        code = self.client.normalize_report_code(report_code)
        fights = self.client.get_fights(code)
        selected = fights if not fight_ids else [f for f in fights if int(f.get("id", -1)) in {int(x) for x in fight_ids}]
        if fight_ids and len(selected) != len(set(map(int, fight_ids))):
            found = {int(f.get("id", -1)) for f in selected}
            missing = sorted(set(map(int, fight_ids)) - found)
            raise ValueError(f"Fight(s) not found in report {code}: {missing}")

        total = {"fights": 0, "actors": 0, "events": 0, "observed_windows": 0}
        for fight in selected:
            result = self.import_fight(code, fight, gap_threshold_ms)
            total["fights"] += 1
            for key in ("actors", "events", "observed_windows"):
                total[key] += result[key]
        return total
