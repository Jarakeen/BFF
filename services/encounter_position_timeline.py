from __future__ import annotations

"""User-owned keyframe timeline for the interactive Raid Map.

The Raid Map itself is an editor.  This module stores named snapshots of that
editor so the UI can teach movement between positions without pretending those
positions are canonical encounter mechanics.
"""

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.planning_artifact_pydantic_schema import validate_position_timeline_document


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
            payload = validate_position_timeline_document(
                json.loads(self.path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"Raid Map position timeline failed to load safely: {exc}") from exc
        steps = tuple(
            PositionTimelineStep(
                name=row["name"],
                note=row["note"],
                duration_seconds=row["duration_seconds"],
                items=tuple(TimelineItemState(**item) for item in row["items"]),
            )
            for row in payload["steps"]
        )
        return PositionTimeline(steps=steps)

    def save(self, timeline: PositionTimeline) -> None:
        payload = validate_position_timeline_document({
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
        })
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        read_back = validate_position_timeline_document(
            json.loads(self.path.read_text(encoding="utf-8"))
        )
        if read_back != payload:
            raise RuntimeError("Raid Map position timeline did not round-trip exactly")

