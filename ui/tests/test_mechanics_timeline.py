from ui.mechanics_timeline import (
    phase_event,
    reviewed_timeline_events,
    unresolved_event,
    visual_for,
)
from ui.theme.colors import Colors


def test_mechanics_timeline_visual_vocabulary_is_distinct_and_stable() -> None:
    assert visual_for("phase").symbol == "◆"
    assert visual_for("phase").color == Colors.GOLD_LIGHT
    assert visual_for("interrupt").symbol == "!"
    assert visual_for("cleanse").symbol == "✦"
    assert visual_for("movement").symbol == "➜"
    assert visual_for("positioning").symbol == "⌖"
    assert visual_for("adds").symbol == "♟"
    assert visual_for("danger").symbol == "▲"
    assert visual_for("unresolved").symbol == "?"


def test_phase_event_includes_symbol_marker_and_color() -> None:
    event = phase_event(marker="25%", label="Execute", detail="Explicit phase.")

    assert event == {
        "marker": "◆ 25%",
        "label": "Execute",
        "detail": "Explicit phase.",
        "color": Colors.GOLD_LIGHT,
    }


def test_reviewed_phase_uses_explicit_canonical_start_threshold() -> None:
    events = reviewed_timeline_events(
        canonical_kind="phase",
        fact_key="phase_2",
        payload={"label": "Phase 2", "starts_at": "70%", "floor": 2},
        evidence_count=3,
    )

    assert events == [
        {
            "marker": "◆ 70%",
            "label": "Phase 2",
            "detail": "Reviewed canonical fact supported by 3 evidence row(s).",
            "color": Colors.GOLD_LIGHT,
        }
    ]


def test_reviewed_transition_expands_each_explicit_health_threshold() -> None:
    events = reviewed_timeline_events(
        canonical_kind="phase_transition",
        fact_key="retreat_thresholds",
        payload={"thresholds": ["70%", "40%"]},
        evidence_count=3,
    )

    assert [event["marker"] for event in events] == ["◆ 70%", "◆ 40%"]
    assert [event["label"] for event in events] == ["Retreat Thresholds", "Retreat Thresholds"]
    assert all("3 evidence row(s)" in event["detail"] for event in events)


def test_reviewed_transition_without_explicit_trigger_stays_unresolved() -> None:
    events = reviewed_timeline_events(
        canonical_kind="phase_transition",
        fact_key="meteor_phase",
        payload={"label": "Meteor Phase"},
        evidence_count=2,
    )

    assert events[0]["marker"] == "?"
    assert events[0]["label"] == "Meteor Phase"
    assert "no explicit displayable trigger" in events[0]["detail"]


def test_unknown_timeline_kind_and_unresolved_event_use_muted_fallback() -> None:
    assert visual_for("not-real") == visual_for("unresolved")
    event = unresolved_event()
    assert event["marker"] == "?"
    assert event["color"] == Colors.TEXT_MUTED
