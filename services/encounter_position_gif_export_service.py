from __future__ import annotations

"""Deterministic frame planning for Raid Map animated GIF exports.

The UI renderer owns pixels. This service owns only timing so exported playback
matches the Position Timeline without depending on wall-clock timers.
"""

from dataclasses import dataclass
import math

from services.encounter_position_timeline import PositionTimeline, bounded_duration


MIN_FPS = 4
MAX_FPS = 30
DEFAULT_FPS = 10
DEFAULT_HOLD_SECONDS = 0.7


@dataclass(frozen=True)
class GifFrameSpec:
    """One deterministic exported frame.

    ``progress`` is the eased transition progress from ``from_index`` to
    ``to_index``. A hold frame has matching indices and progress 1.0.
    """

    from_index: int
    to_index: int
    progress: float
    caption_index: int


def bounded_fps(value: int | float) -> int:
    try:
        fps = int(round(float(value)))
    except (TypeError, ValueError):
        fps = DEFAULT_FPS
    return max(MIN_FPS, min(MAX_FPS, fps))


def bounded_hold_seconds(value: int | float) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = DEFAULT_HOLD_SECONDS
    return max(0.0, min(5.0, seconds))


def smoothstep(progress: float) -> float:
    p = max(0.0, min(1.0, float(progress)))
    return p * p * (3.0 - 2.0 * p)


def build_frame_plan(
    timeline: PositionTimeline,
    *,
    fps: int = DEFAULT_FPS,
    hold_seconds: float = DEFAULT_HOLD_SECONDS,
) -> tuple[GifFrameSpec, ...]:
    """Return a fixed-rate frame plan including a short hold on every step."""

    steps = tuple(timeline.steps)
    if not steps:
        return ()

    rate = bounded_fps(fps)
    hold = bounded_hold_seconds(hold_seconds)
    hold_frames = max(1, int(round(hold * rate))) if hold > 0 else 1

    frames: list[GifFrameSpec] = [
        GifFrameSpec(0, 0, 1.0, 0) for _ in range(hold_frames)
    ]

    for target_index in range(1, len(steps)):
        source_index = target_index - 1
        duration = bounded_duration(steps[target_index].duration_seconds)
        transition_frames = max(1, int(math.ceil(duration * rate)))
        for frame_number in range(1, transition_frames + 1):
            linear = frame_number / transition_frames
            frames.append(
                GifFrameSpec(
                    source_index,
                    target_index,
                    smoothstep(linear),
                    target_index,
                )
            )
        frames.extend(
            GifFrameSpec(target_index, target_index, 1.0, target_index)
            for _ in range(hold_frames)
        )

    return tuple(frames)
