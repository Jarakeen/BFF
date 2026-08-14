# services/stream_event_service.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class StreamEventService:
    """Writes a small trigger file the OBS Lua script polls (same pattern as
    CurrentExpedition.json/CurrentIncident.json). Each fire() bumps a
    Sequence number so Lua can tell "this is a new request" apart from
    "nothing changed since last poll" - a plain field like ChapterLabel
    can't do that on its own since two events in a row could share a label
    (e.g. "BRB" twice).

    Also persists simple per-stream counters (total pulls, current boss's
    pulls/wipes) so an app restart mid-stream doesn't lose them.
    """

    def __init__(self, events_path: Path, session_path: Path, boss_log_path: Path) -> None:
        self.events_path = events_path
        self.session_path = session_path
        self.boss_log_path = boss_log_path

    def _next_sequence(self) -> int:
        if not self.events_path.exists():
            return 1
        try:
            data = json.loads(self.events_path.read_text(encoding="utf-8"))
            return int(data.get("Sequence", 0)) + 1
        except (json.JSONDecodeError, OSError, ValueError):
            return 1

    def fire_event(
        self,
        chapter_label: str = "",
        scene_name: str = "",
        narrator_text: str = "",
        log_label: str = "",
    ) -> None:
        payload = {
            "Sequence": self._next_sequence(),
            "ChapterLabel": chapter_label,
            "SceneName": scene_name,
            "NarratorText": narrator_text,
            "LogLabel": log_label,
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.write_text(json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8")

    def load_session(self) -> dict:
        defaults = { "TotalPulls": 0,
    "CurrentBoss": "",
    "BossPulls": 0,
    "BossWipes": 0,
    "Events": [],}
        if not self.session_path.exists():
            return defaults
        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
            defaults.update(data)
            return defaults
        except (json.JSONDecodeError, OSError):
            return defaults

    def save_session(self, session: dict) -> None:
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(json.dumps(session, ensure_ascii=False, indent=4), encoding="utf-8")

    def append_boss_log(self, boss: str, pulls: int, wipes: int) -> None:
        self.boss_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = (
            f"{datetime.now().isoformat(timespec='seconds')} | "
            f"{boss or 'Unnamed Boss'} | Pulls: {pulls} | Wipes: {wipes}\n"
        )
        with self.boss_log_path.open("a", encoding="utf-8") as f:
            f.write(line)
