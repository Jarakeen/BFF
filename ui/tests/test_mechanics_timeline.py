from ui.mechanics_timeline import phase_event, unresolved_event, visual_for
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


def test_unknown_timeline_kind_and_unresolved_event_use_muted_fallback() -> None:
    assert visual_for("not-real") == visual_for("unresolved")
    event = unresolved_event()
    assert event["marker"] == "?"
    assert event["color"] == Colors.TEXT_MUTED
