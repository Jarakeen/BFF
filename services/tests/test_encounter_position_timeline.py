from pathlib import Path

from services.encounter_position_timeline import (
    PositionTimeline,
    PositionTimelineStep,
    PositionTimelineStore,
    TimelineItemState,
    bounded_duration,
    item_key,
)


def test_item_key_is_stable_and_case_insensitive() -> None:
    assert item_key("token", "Healer", "Healer 1") == item_key(
        "TOKEN", "healer", "  healer   1  "
    )


def test_duration_is_bounded() -> None:
    assert bounded_duration(0.01) == 0.2
    assert bounded_duration(2.5) == 2.5
    assert bounded_duration(99.0) == 30.0


def test_store_round_trips_steps_and_items(tmp_path: Path) -> None:
    path = tmp_path / "encounter_positioning_timeline.json"
    store = PositionTimelineStore(path)
    timeline = PositionTimeline(
        steps=(
            PositionTimelineStep(
                name="Pull",
                note="Main tank center",
                duration_seconds=1.5,
                items=(
                    TimelineItemState(
                        item_id="token:tank:main tank:1",
                        family="token",
                        kind="tank",
                        label="Main Tank",
                        x=0.5,
                        y=0.35,
                        radius=18.0,
                    ),
                ),
            ),
            PositionTimelineStep(
                name="Spread",
                note="Healers split",
                duration_seconds=2.0,
                items=(),
            ),
        )
    )

    store.save(timeline)
    loaded = store.load()

    assert loaded == timeline


def test_store_returns_empty_timeline_for_bad_json(tmp_path: Path) -> None:
    path = tmp_path / "encounter_positioning_timeline.json"
    path.write_text("not-json", encoding="utf-8")

    assert PositionTimelineStore(path).load() == PositionTimeline()
