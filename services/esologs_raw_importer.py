from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.esologs_combat_importer import EsoLogsCombatImporter
from services.esologs_importer import EsoLogsImporter


class EsoLogsRawImporter(EsoLogsCombatImporter):
    """Import previously captured ESO Logs probe JSON without network access."""

    def __init__(self, connection: sqlite3.Connection):
        super().__init__(connection, client=None)  # type: ignore[arg-type]
        self.manifest = EsoLogsImporter(connection, client=None)  # type: ignore[arg-type]

    @staticmethod
    def _load(path: Path) -> dict[str, Any] | None:
        """Load an ESO Logs probe export; return None for unrelated raw JSON."""
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        # data/raw also contains other project JSON exports. Only probe exports
        # with a report_code are inputs for this importer.
        if not str(payload.get("report_code") or "").strip():
            return None
        return payload

    @staticmethod
    def _fight_items(fights: Any) -> list[tuple[str, dict[str, Any]]]:
        """Normalize probe exports where fights may be a dict or a list."""
        if isinstance(fights, dict):
            return [(str(key), value) for key, value in fights.items() if isinstance(value, dict)]
        if isinstance(fights, list):
            items: list[tuple[str, dict[str, Any]]] = []
            for index, value in enumerate(fights):
                if not isinstance(value, dict):
                    continue
                metadata = value.get("metadata") or {}
                fight_id = metadata.get("id", value.get("id", index))
                items.append((str(fight_id), value))
            return items
        return []

    @staticmethod
    def _metadata(fight: dict[str, Any]) -> dict[str, Any]:
        metadata = fight.get("metadata")
        return metadata if isinstance(metadata, dict) else fight

    @staticmethod
    def _timestamp_text(path: Path) -> str:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

    def _import_fight_raw(self, *, report_code: str, fight: dict[str, Any], source_path: Path, gap_threshold_ms: float) -> dict[str, int]:
        metadata = self._metadata(fight)
        if metadata.get("id") is None:
            raise ValueError(f"{source_path.name}: fight is missing metadata.id")

        fight_id = int(metadata["id"])
        events = fight.get("events") or []
        if not isinstance(events, list):
            raise ValueError(f"{source_path.name}: fight {fight_id} events must be a list")
        player_details = fight.get("player_details") or {}
        if not isinstance(player_details, dict):
            player_details = {}

        self.connection.execute(
            """
            INSERT INTO log_report (report_code, title, source_url, fetched_at, raw_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(report_code) DO UPDATE SET
                title=excluded.title, source_url=excluded.source_url,
                fetched_at=excluded.fetched_at, raw_json=excluded.raw_json
            """,
            (report_code, None, f"https://www.esologs.com/reports/{report_code}",
             self._timestamp_text(source_path),
             json.dumps({"source_file": str(source_path), "fight": metadata}, ensure_ascii=False)),
        )
        self.connection.execute(
            """
            INSERT OR REPLACE INTO log_fight (
                report_code, fight_id, name, kill, difficulty, boss_percentage,
                start_time, end_time, encounter_id, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (report_code, fight_id, metadata.get("name"),
             int(bool(metadata.get("kill"))) if metadata.get("kill") is not None else None,
             metadata.get("difficulty"), metadata.get("bossPercentage"),
             metadata.get("startTime"), metadata.get("endTime"), metadata.get("encounterID"),
             json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
        )

        self.connection.execute("DELETE FROM log_actor WHERE report_code=? AND fight_id=?", (report_code, fight_id))
        actor_count = 0
        for role_key, role_name in (("healers", "healer"), ("tanks", "tank"), ("dps", "dps")):
            for actor in player_details.get(role_key) or []:
                if not isinstance(actor, dict):
                    continue
                actor_id = int(actor.get("id", -1))
                if actor_id < 0:
                    continue
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO log_actor (
                        report_code, fight_id, actor_id, guid, name, display_name,
                        actor_type, role, anonymous, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (report_code, fight_id, actor_id, actor.get("guid"), actor.get("name"),
                     actor.get("displayName"), actor.get("type"), role_name,
                     int(bool(actor.get("anonymous"))), json.dumps(actor, ensure_ascii=False, sort_keys=True)),
                )
                actor_count += 1

        self.connection.execute("DELETE FROM log_event WHERE report_code=? AND fight_id=?", (report_code, fight_id))
        valid_events = 0
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue
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
                (report_code, fight_id, index, float(event.get("timestamp", 0)), event.get("type", "unknown"),
                 event.get("sourceID"),
                 None if event.get("sourceIsFriendly") is None else int(bool(event.get("sourceIsFriendly"))),
                 event.get("targetID"), event.get("targetInstance"),
                 None if event.get("targetIsFriendly") is None else int(bool(event.get("targetIsFriendly"))),
                 event.get("abilityGameID"), event.get("extraAbilityGameID"), event.get("amount"),
                 event.get("hitType"), event.get("tick"), event.get("castTrackID"), event.get("resourceChange"),
                 event.get("resourceChangeType"), event.get("otherResourceChange"), event.get("maxResourceAmount"),
                 event.get("waste"), event.get("overheal"), event.get("absorbed"), event.get("stack"),
                 json.dumps(event, ensure_ascii=False, sort_keys=True)),
            )
            valid_events += 1

        windows = self._rebuild_observed_windows(report_code, metadata, gap_threshold_ms=gap_threshold_ms)
        self.connection.commit()
        return {"actors": actor_count, "events": valid_events, "observed_windows": windows}

    def import_directory(self, raw_dir: Path, gap_threshold_ms: float = 3000.0) -> dict[str, int]:
        files = sorted(raw_dir.glob("*.json"))
        if not files:
            raise FileNotFoundError(f"No JSON files found in {raw_dir}")

        totals = {"files": 0, "fights": 0, "actors": 0, "events": 0, "observed_windows": 0}
        seen: set[tuple[str, int]] = set()
        skipped = 0

        for path in files:
            payload = self._load(path)
            if payload is None:
                skipped += 1
                continue
            report_code = str(payload.get("report_code") or "").strip()
            fight_items = self._fight_items(payload.get("fights"))
            imported_from_file = 0
            for fight_key, fight in fight_items:
                metadata = self._metadata(fight)
                fight_id = int(metadata.get("id", fight_key))
                key = (report_code, fight_id)
                if key in seen:
                    continue
                result = self._import_fight_raw(report_code=report_code, fight=fight, source_path=path, gap_threshold_ms=gap_threshold_ms)
                seen.add(key)
                imported_from_file += 1
                totals["fights"] += 1
                totals["actors"] += result["actors"]
                totals["events"] += result["events"]
                totals["observed_windows"] += result["observed_windows"]

            if imported_from_file:
                totals["files"] += 1
                manifest_id = self.manifest._manifest_start(
                    export_name=path.name, export_type="raw_probe_json", report_code=report_code,
                    request={"source_file": str(path)},
                    destination_tables=["log_report", "log_fight", "log_actor", "log_event", "log_observed_target", "log_observed_damage_window"],
                )
                self.manifest._manifest_finish(manifest_id, status="imported", record_count=imported_from_file)

        if skipped:
            print(f"Skipped {skipped} unrelated JSON files in {raw_dir}.")
        return totals
