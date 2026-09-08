from services.encounter_position_gif_export_service import (
    GifFrameSpec,
    bounded_fps,
    build_frame_plan,
    smoothstep,
)
from services.encounter_position_timeline import (
    PositionTimeline,
    PositionTimelineStep,
)


def test_gif_frame_plan_holds_first_step_and_animates_into_next() -> None:
    timeline = PositionTimeline(
        steps=(
            PositionTimelineStep(name="Pull", duration_seconds=1.0),
            PositionTimelineStep(name="Spread", duration_seconds=1.0),
        )
    )

    frames = build_frame_plan(timeline, fps=10, hold_seconds=0.5)

    assert len(frames) == 20
    assert frames[:5] == (GifFrameSpec(0, 0, 1.0, 0),) * 5
    assert frames[5].from_index == 0
    assert frames[5].to_index == 1
    assert 0.0 < frames[5].progress < 1.0
    assert frames[-1] == GifFrameSpec(1, 1, 1.0, 1)


def test_gif_frame_plan_uses_target_step_move_duration() -> None:
    timeline = PositionTimeline(
        steps=(
            PositionTimelineStep(name="Pull", duration_seconds=9.0),
            PositionTimelineStep(name="Transition", duration_seconds=2.0),
        )
    )

    frames = build_frame_plan(timeline, fps=8, hold_seconds=0.0)
    transition = [frame for frame in frames if frame.from_index == 0 and frame.to_index == 1]

    assert len(transition) == 16
    assert transition[-1].progress == 1.0


def test_gif_frame_plan_handles_empty_timeline() -> None:
    assert build_frame_plan(PositionTimeline()) == ()


def test_gif_timing_bounds_and_smoothstep_are_deterministic() -> None:
    assert bounded_fps(1) == 4
    assert bounded_fps(999) == 30
    assert smoothstep(-1.0) == 0.0
    assert smoothstep(0.5) == 0.5
    assert smoothstep(2.0) == 1.0
