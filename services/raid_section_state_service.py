from __future__ import annotations

"""Small user-owned state store for Readiness and Live Raid.

This is deliberately separate from canonical ESO data and RaidPlan mechanics. It stores
only explicit human decisions and manual run bookkeeping. Unknown runtime evidence remains
unknown; this service never manufactures telemetry.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from engine.config import get_app_root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class RaidRunEvent:
    timestamp: str
    plan_id: str
    kind: str
    text: str
    evidence: str = "MANUAL"


@dataclass(frozen=True)
class RaidRunAttempt:
    plan_id: str
    attempt: int
    encounter_id: str
    started_at: str
    ended_at: str
    duration_seconds: int | None


class RaidSectionStateService:
    """Persist explicit readiness and manual run state without touching eso.db."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else get_app_root() / "user_data" / "raid_section_state.json"

    def _read(self) -> dict:
        if not self.path.exists():
            return {
                "human_ready": {},
                "runs": {},
                "events": [],
                "reviews": [],
                "attempts": [],
                "raid_map_links": {},
            }
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("human_ready", {})
        payload.setdefault("runs", {})
        payload.setdefault("events", [])
        payload.setdefault("reviews", [])
        payload.setdefault("attempts", [])
        payload.setdefault("raid_map_links", {})
        return payload

    def _write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def human_ready(self, plan_id: str, seat_id: str) -> bool | None:
        payload = self._read()
        value = payload.get("human_ready", {}).get(_clean(plan_id), {}).get(_clean(seat_id))
        return value if isinstance(value, bool) else None

    def set_human_ready(self, plan_id: str, seat_id: str, ready: bool | None) -> None:
        payload = self._read()
        plans = payload.setdefault("human_ready", {})
        seats = plans.setdefault(_clean(plan_id), {})
        if ready is None:
            seats.pop(_clean(seat_id), None)
        else:
            seats[_clean(seat_id)] = bool(ready)
        self._write(payload)

    def run_state(self, plan_id: str) -> dict:
        payload = self._read()
        state = payload.get("runs", {}).get(_clean(plan_id), {})
        return dict(state) if isinstance(state, dict) else {}

    def run_notes(self, plan_id: str) -> str:
        return _clean(self.run_state(plan_id).get("notes"))

    def selected_encounter_id(self, plan_id: str) -> str:
        return _clean(self.run_state(plan_id).get("encounter_id"))

    def linked_raid_map_id(self, plan_id: str, encounter_id: str) -> str:
        payload = self._read()
        links = payload.get("raid_map_links", {})
        plan_links = links.get(_clean(plan_id), {}) if isinstance(links, dict) else {}
        if not isinstance(plan_links, dict):
            return ""
        return _clean(plan_links.get(_clean(encounter_id)))

    def set_linked_raid_map_id(
        self,
        plan_id: str,
        encounter_id: str,
        map_id: str,
    ) -> None:
        plan_key = _clean(plan_id)
        encounter_key = _clean(encounter_id)
        if not plan_key or not encounter_key:
            raise ValueError("plan_id and encounter_id are required for a Raid Map link")
        payload = self._read()
        links = payload.setdefault("raid_map_links", {})
        plan_links = links.setdefault(plan_key, {})
        value = _clean(map_id)
        if value:
            plan_links[encounter_key] = value
        else:
            plan_links.pop(encounter_key, None)
            if not plan_links:
                links.pop(plan_key, None)
        self._write(payload)

    def set_selected_encounter_id(self, plan_id: str, encounter_id: str) -> dict:
        payload = self._read()
        runs = payload.setdefault("runs", {})
        state = dict(runs.get(_clean(plan_id), {}))
        state["encounter_id"] = _clean(encounter_id)
        runs[_clean(plan_id)] = state
        self._write(payload)
        return dict(state)

    def set_run_notes(self, plan_id: str, notes: str) -> dict:
        payload = self._read()
        runs = payload.setdefault("runs", {})
        state = dict(runs.get(_clean(plan_id), {}))
        cleaned = _clean(notes)
        changed = _clean(state.get("notes")) != cleaned
        state["notes"] = cleaned
        runs[_clean(plan_id)] = state
        if changed:
            self._append_event_payload(payload, plan_id, "run_notes", "Run notes updated", "MANUAL")
        self._write(payload)
        return dict(state)

    def save_review_note(
        self,
        *,
        plan_id: str,
        trial_id: str,
        plan_name: str,
        attempt: int,
        notes: str,
        started_at: str = "",
        ended_at: str = "",
        encounter_id: str = "",
    ) -> dict | None:
        """Upsert the durable review note for one Raid Plan attempt."""
        cleaned = _clean(notes)
        if not cleaned:
            return None

        payload = self._read()
        reviews = payload.setdefault("reviews", [])
        now = _now()
        plan_key = _clean(plan_id)
        attempt_number = max(0, int(attempt or 0))
        existing = next(
            (
                row
                for row in reviews
                if isinstance(row, dict)
                and _clean(row.get("plan_id")) == plan_key
                and int(row.get("attempt", 0) or 0) == attempt_number
            ),
            None,
        )

        if existing is None:
            existing = {
                "review_id": f"{plan_key}:{attempt_number}",
                "plan_id": plan_key,
                "trial_id": _clean(trial_id),
                "plan_name": _clean(plan_name),
                "attempt": attempt_number,
                "created_at": now,
            }
            reviews.append(existing)

        existing["trial_id"] = _clean(trial_id)
        existing["plan_name"] = _clean(plan_name)
        existing["notes"] = cleaned
        existing["encounter_id"] = _clean(encounter_id) or _clean(existing.get("encounter_id"))
        existing["started_at"] = _clean(started_at) or _clean(existing.get("started_at"))
        existing["ended_at"] = _clean(ended_at) or _clean(existing.get("ended_at"))
        existing["updated_at"] = now
        self._set_review_duration(existing)
        self._write(payload)
        return dict(existing)

    @staticmethod
    def _set_review_duration(review: dict) -> None:
        started = _clean(review.get("started_at"))
        ended = _clean(review.get("ended_at"))
        if not started or not ended:
            review["duration_seconds"] = None
            return
        try:
            start_dt = datetime.fromisoformat(started)
            end_dt = datetime.fromisoformat(ended)
        except ValueError:
            review["duration_seconds"] = None
            return
        review["duration_seconds"] = max(
            0,
            int((end_dt - start_dt).total_seconds()),
        )

    @classmethod
    def _update_review_timing_payload(
        cls,
        payload: dict,
        *,
        plan_id: str,
        attempt: int,
        started_at: str,
        ended_at: str,
    ) -> None:
        plan_key = _clean(plan_id)
        attempt_number = max(0, int(attempt or 0))
        for review in payload.setdefault("reviews", []):
            if not isinstance(review, dict):
                continue
            if (
                _clean(review.get("plan_id")) == plan_key
                and int(review.get("attempt", 0) or 0) == attempt_number
            ):
                review["started_at"] = _clean(started_at) or _clean(review.get("started_at"))
                review["ended_at"] = _clean(ended_at) or _clean(review.get("ended_at"))
                cls._set_review_duration(review)
                return

    @staticmethod
    def _set_attempt_duration(attempt: dict) -> None:
        started = _clean(attempt.get("started_at"))
        ended = _clean(attempt.get("ended_at"))
        if not started or not ended:
            attempt["duration_seconds"] = None
            return
        try:
            start_dt = datetime.fromisoformat(started)
            end_dt = datetime.fromisoformat(ended)
        except ValueError:
            attempt["duration_seconds"] = None
            return
        attempt["duration_seconds"] = max(
            0,
            int((end_dt - start_dt).total_seconds()),
        )

    @classmethod
    def _upsert_attempt_payload(
        cls,
        payload: dict,
        *,
        plan_id: str,
        attempt: int,
        encounter_id: str,
        started_at: str,
        ended_at: str,
    ) -> dict:
        plan_key = _clean(plan_id)
        attempt_number = max(0, int(attempt or 0))
        rows = payload.setdefault("attempts", [])
        existing = next(
            (
                row
                for row in rows
                if isinstance(row, dict)
                and _clean(row.get("plan_id")) == plan_key
                and int(row.get("attempt", 0) or 0) == attempt_number
            ),
            None,
        )
        if existing is None:
            existing = {
                "plan_id": plan_key,
                "attempt": attempt_number,
            }
            rows.append(existing)
        existing["encounter_id"] = _clean(encounter_id)
        existing["started_at"] = _clean(started_at) or _clean(existing.get("started_at"))
        existing["ended_at"] = _clean(ended_at) or _clean(existing.get("ended_at"))
        cls._set_attempt_duration(existing)
        return existing

    def attempt_history(
        self,
        plan_id: str,
        *,
        encounter_id: str = "",
    ) -> tuple[RaidRunAttempt, ...]:
        payload = self._read()
        plan_key = _clean(plan_id)
        encounter_key = _clean(encounter_id)
        rows = []
        for row in payload.get("attempts", []):
            if not isinstance(row, dict):
                continue
            if _clean(row.get("plan_id")) != plan_key:
                continue
            if encounter_key and _clean(row.get("encounter_id")) != encounter_key:
                continue
            duration = row.get("duration_seconds")
            rows.append(
                RaidRunAttempt(
                    plan_id=plan_key,
                    attempt=max(0, int(row.get("attempt", 0) or 0)),
                    encounter_id=_clean(row.get("encounter_id")),
                    started_at=_clean(row.get("started_at")),
                    ended_at=_clean(row.get("ended_at")),
                    duration_seconds=(
                        max(0, int(duration))
                        if isinstance(duration, int) and not isinstance(duration, bool)
                        else None
                    ),
                )
            )
        rows.sort(key=lambda row: (row.attempt, row.started_at), reverse=True)
        return tuple(rows)

    def review_notes(self) -> tuple[dict, ...]:
        """Return review notes newest first without inventing missing run metadata."""
        payload = self._read()
        rows = [
            dict(row)
            for row in payload.get("reviews", [])
            if isinstance(row, dict) and _clean(row.get("notes"))
        ]
        rows.sort(
            key=lambda row: _clean(row.get("updated_at") or row.get("created_at")),
            reverse=True,
        )
        return tuple(rows)

    def start_pull(self, plan_id: str, *, encounter_id: str = "") -> dict:
        payload = self._read()
        runs = payload.setdefault("runs", {})
        prior = runs.get(_clean(plan_id), {})
        attempt = int(prior.get("attempt", 0) or 0) + 1
        state = {
            "attempt": attempt,
            "active": True,
            "started_at": _now(),
            "ended_at": "",
            "notes_paused": False,
            "notes": _clean(prior.get("notes")),
            "encounter_id": _clean(encounter_id) or _clean(prior.get("encounter_id")),
        }
        runs[_clean(plan_id)] = state
        self._upsert_attempt_payload(
            payload,
            plan_id=plan_id,
            attempt=attempt,
            encounter_id=_clean(state.get("encounter_id")),
            started_at=_clean(state.get("started_at")),
            ended_at="",
        )
        self._append_event_payload(payload, plan_id, "pull_started", f"Pull #{attempt} started", "MANUAL")
        self._write(payload)
        return dict(state)

    def set_notes_paused(self, plan_id: str, paused: bool) -> dict:
        payload = self._read()
        runs = payload.setdefault("runs", {})
        state = dict(runs.get(_clean(plan_id), {}))
        state["notes_paused"] = bool(paused)
        runs[_clean(plan_id)] = state
        self._append_event_payload(payload, plan_id, "notes", "Run notes paused" if paused else "Run notes resumed", "MANUAL")
        self._write(payload)
        return dict(state)

    def end_attempt(self, plan_id: str) -> dict:
        payload = self._read()
        runs = payload.setdefault("runs", {})
        state = dict(runs.get(_clean(plan_id), {}))
        state["active"] = False
        state["ended_at"] = _now()
        runs[_clean(plan_id)] = state
        attempt = int(state.get("attempt", 0) or 0)
        self._upsert_attempt_payload(
            payload,
            plan_id=plan_id,
            attempt=attempt,
            encounter_id=_clean(state.get("encounter_id")),
            started_at=_clean(state.get("started_at")),
            ended_at=_clean(state.get("ended_at")),
        )
        self._update_review_timing_payload(
            payload,
            plan_id=plan_id,
            attempt=attempt,
            started_at=_clean(state.get("started_at")),
            ended_at=_clean(state.get("ended_at")),
        )
        self._append_event_payload(payload, plan_id, "attempt_ended", f"Attempt #{attempt} ended", "MANUAL")
        self._write(payload)
        return dict(state)

    @staticmethod
    def _append_event_payload(payload: dict, plan_id: str, kind: str, text: str, evidence: str) -> None:
        events = payload.setdefault("events", [])
        events.append({
            "timestamp": _now(),
            "plan_id": _clean(plan_id),
            "kind": _clean(kind),
            "text": _clean(text),
            "evidence": _clean(evidence).upper() or "MANUAL",
        })
        del events[:-200]

    def add_event(self, plan_id: str, kind: str, text: str, *, evidence: str = "MANUAL") -> None:
        payload = self._read()
        self._append_event_payload(payload, plan_id, kind, text, evidence)
        self._write(payload)

    def events(self, plan_id: str, *, limit: int = 12) -> tuple[RaidRunEvent, ...]:
        payload = self._read()
        rows = [
            row for row in payload.get("events", [])
            if isinstance(row, dict) and _clean(row.get("plan_id")) == _clean(plan_id)
        ]
        rows = rows[-max(0, int(limit)):]
        rows.reverse()
        return tuple(
            RaidRunEvent(
                timestamp=_clean(row.get("timestamp")),
                plan_id=_clean(row.get("plan_id")),
                kind=_clean(row.get("kind")),
                text=_clean(row.get("text")),
                evidence=_clean(row.get("evidence")).upper() or "MANUAL",
            )
            for row in rows
        )


__all__ = ["RaidRunAttempt", "RaidRunEvent", "RaidSectionStateService"]
