from __future__ import annotations

"""User-owned keyframe timeline for the interactive Raid Map.

The Raid Map itself is an editor.  This module stores named snapshots of that
editor so the UI can teach movement between positions without pretending those
positions are canonical encounter mechanics.
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


SCHEMA_VERSION = 1
DEFAULT_STEP_SECONDS = 2.0
MIN_STEP_SECONDS = 0.2
MAX_STEP_SECONDS = 30.0


@dataclass(frozen=True)
class TimelineItemState:
    item_id: str
    family: str
    kind: str
    label: str
    x: float
    y: float
    radius: float = 0.0
    visible: bool = True


@dataclass(frozen=True)
class PositionTimelineStep:
    name: str
    note: str = ""
    duration_seconds: float = DEFAULT_STEP_SECONDS
    items: tuple[TimelineItemState, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PositionTimeline:
    steps: tuple[PositionTimelineStep, ...] = field(default_factory=tuple)


def bounded_duration(value: float) -> float:
    return max(MIN_STEP_SECONDS, min(MAX_STEP_SECONDS, float(value)))


def item_key(family: str, kind: str, label: str, ordinal: int = 1) -> str:
    """Build a deterministic item identity from the existing board model.

    EncounterBoard does not yet persist UUIDs for markers.  Kind + label is the
    stable human identity it already owns, with an ordinal only for duplicate
    labels.  This keeps the timeline backward-compatible with existing saved
    boards instead of changing encounter_positioning.json underneath users.
    """

    clean_family = str(family or "item").strip().casefold() or "item"
    clean_kind = str(kind or "item").strip().casefold() or "item"
    clean_label = " ".join(str(label or clean_kind).split()).casefold()
    return f"{clean_family}:{clean_kind}:{clean_label}:{max(1, int(ordinal))}"


class PositionTimelineStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> PositionTimeline:
        if not self.path.exists():
            return PositionTimeline()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return PositionTimeline()
        if not isinstance(payload, dict):
            return PositionTimeline()
        raw_steps = payload.get("steps", [])
        if not isinstance(raw_steps, list):
            return PositionTimeline()

        steps: list[PositionTimelineStep] = []
        for raw_step in raw_steps:
            if not isinstance(raw_step, dict):
                continue
            raw_items = raw_step.get("items", [])
            if not isinstance(raw_items, list):
                raw_items = []
            items: list[TimelineItemState] = []
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                item_id = str(raw_item.get("item_id", "") or "").strip()
                if not item_id:
                    continue
                try:
                    items.append(
                        TimelineItemState(
                            item_id=item_id,
                            family=str(raw_item.get("family", "token") or "token"),
                            kind=str(raw_item.get("kind", "") or ""),
                            label=str(raw_item.get("label", "") or ""),
                            x=float(raw_item.get("x", 0.5)),
                            y=float(raw_item.get("y", 0.5)),
                            radius=float(raw_item.get("radius", 0.0) or 0.0),
                            visible=bool(raw_item.get("visible", True)),
                        )
                    )
                except (TypeError, ValueError):
                    continue
            name = str(raw_step.get("name", "") or "").strip() or f"Step {len(steps) + 1}"
            note = str(raw_step.get("note", "") or "")
            try:
                duration = bounded_duration(float(raw_step.get("duration_seconds", DEFAULT_STEP_SECONDS)))
            except (TypeError, ValueError):
                duration = DEFAULT_STEP_SECONDS
            steps.append(
                PositionTimelineStep(
                    name=name,
                    note=note,
                    duration_seconds=duration,
                    items=tuple(items),
                )
            )
        return PositionTimeline(steps=tuple(steps))

    def save(self, timeline: PositionTimeline) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "steps": [
                {
                    "name": step.name,
                    "note": step.note,
                    "duration_seconds": bounded_duration(step.duration_seconds),
                    "items": [asdict(item) for item in step.items],
                }
                for step in timeline.steps
            ],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
