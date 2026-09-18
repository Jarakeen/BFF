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


class RaidSectionStateService:
    """Persist explicit readiness and manual run state without touching eso.db."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else get_app_root() / "user_data" / "raid_section_state.json"

    def _read(self) -> dict:
        if not self.path.exists():
            return {"human_ready": {}, "runs": {}, "events": [], "reviews": []}
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
        existing["updated_at"] = now
        self._write(payload)
        return dict(existing)

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

    def start_pull(self, plan_id: str) -> dict:
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
        }
        runs[_clean(plan_id)] = state
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


__all__ = ["RaidRunEvent", "RaidSectionStateService"]
