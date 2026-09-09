from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.rotation_plan import RotationActionKind, RotationPlan
from ui.rotation_duration_evidence_support import RotationDurationEvidence


@dataclass(frozen=True)
class RotationTimelineAction:
    time_seconds: float
    sequence: int
    name: str
    kind: str
    bar: str | None
    icon_key: str


@dataclass(frozen=True)
class RotationTimelineSegment:
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class RotationTimelineLane:
    lane_key: str
    label: str
    bar: str
    duration_seconds: float
    segments: tuple[RotationTimelineSegment, ...]


@dataclass(frozen=True)
class RotationTimelineProjection:
    duration_seconds: float
    actions: tuple[RotationTimelineAction, ...]
    lanes: tuple[RotationTimelineLane, ...]
    unresolved: tuple[str, ...]


class RotationTimelineProjectionService:
    """Project canonical rotation evidence into a read-only timeline model.

    This service does not resolve ESO durations. It consumes the authoritative
    RotationPlan and optional already-resolved RotationDurationEvidence and only
    converts them into geometry-friendly UI evidence.
    """

    _ICON_KINDS = {
        RotationActionKind.SKILL,
        RotationActionKind.ULTIMATE,
    }

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")
        return cleaned or "unknown_skill"

    @staticmethod
    def _normalized_bar(value: str | None) -> str:
        normalized = str(value or "any").strip().casefold()
        return normalized if normalized in {"front", "back"} else "any"

    @staticmethod
    def _merge_segments(
        segments: list[RotationTimelineSegment],
    ) -> tuple[RotationTimelineSegment, ...]:
        if not segments:
            return ()

        ordered = sorted(segments, key=lambda item: (item.start_seconds, item.end_seconds))
        merged: list[RotationTimelineSegment] = [ordered[0]]
        for segment in ordered[1:]:
            previous = merged[-1]
            if segment.start_seconds <= previous.end_seconds:
                merged[-1] = RotationTimelineSegment(
                    start_seconds=previous.start_seconds,
                    end_seconds=max(previous.end_seconds, segment.end_seconds),
                )
            else:
                merged.append(segment)
        return tuple(merged)

    def project(
        self,
        plan: RotationPlan,
        *,
        duration_evidence: RotationDurationEvidence | None = None,
    ) -> RotationTimelineProjection:
        actions = tuple(
            RotationTimelineAction(
                time_seconds=float(action.time_seconds),
                sequence=int(action.sequence),
                name=str(action.name or action.kind.value.replace("_", " ").title()),
                kind=action.kind.value,
                bar=action.bar,
                icon_key=self._slug(
                    str(action.name or action.kind.value.replace("_", " ").title())
                ),
            )
            for action in plan.actions
            if action.kind in self._ICON_KINDS
        )

        lanes: list[RotationTimelineLane] = []
        if duration_evidence is not None:
            for row in duration_evidence.rows:
                duration = max(0.0, float(row.duration_seconds))
                if duration <= 0.0:
                    continue

                row_bar = self._normalized_bar(row.bar)
                row_name = str(row.ability).strip()
                row_key = row_name.casefold()
                segments: list[RotationTimelineSegment] = []

                for action in plan.actions:
                    if action.kind not in self._ICON_KINDS:
                        continue
                    if str(action.name or "").strip().casefold() != row_key:
                        continue
                    action_bar = self._normalized_bar(action.bar)
                    if row_bar != "any" and action_bar != row_bar:
                        continue

                    start = float(action.time_seconds)
                    end = min(float(plan.duration_seconds), start + duration)
                    if end <= start:
                        continue
                    segments.append(
                        RotationTimelineSegment(
                            start_seconds=start,
                            end_seconds=end,
                        )
                    )

                if not segments:
                    continue

                lane_bar = row_bar
                lanes.append(
                    RotationTimelineLane(
                        lane_key=f"{self._slug(row_name)}:{lane_bar}",
                        label=row_name,
                        bar=lane_bar,
                        duration_seconds=duration,
                        segments=self._merge_segments(segments),
                    )
                )

        unresolved = list(plan.unresolved)
        if duration_evidence is not None:
            unresolved.extend(duration_evidence.unresolved)

        return RotationTimelineProjection(
            duration_seconds=float(plan.duration_seconds),
            actions=actions,
            lanes=tuple(lanes),
            unresolved=tuple(dict.fromkeys(str(item) for item in unresolved if str(item))),
        )


__all__ = [
    "RotationTimelineAction",
    "RotationTimelineLane",
    "RotationTimelineProjection",
    "RotationTimelineProjectionService",
    "RotationTimelineSegment",
]
