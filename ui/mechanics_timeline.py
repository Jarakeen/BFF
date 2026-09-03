from __future__ import annotations

"""Visual vocabulary for the Mechanics boss timeline.

The timeline receives source-backed encounter events from services. This module
only chooses presentation semantics for already-classified event kinds; it does
not infer mechanics, timing, player strategy, or severity from prose.
"""

from dataclasses import dataclass

from ui.theme.colors import Colors


@dataclass(frozen=True)
class TimelineVisual:
    symbol: str
    color: str


TIMELINE_VISUALS: dict[str, TimelineVisual] = {
    "phase": TimelineVisual("◆", Colors.GOLD_LIGHT),
    "interrupt": TimelineVisual("!", Colors.WARNING),
    "cleanse": TimelineVisual("✦", Colors.ACCENT_LIGHT),
    "movement": TimelineVisual("➜", Colors.ACCENT),
    "positioning": TimelineVisual("⌖", Colors.INFO),
    "adds": TimelineVisual("♟", Colors.GOLD),
    "danger": TimelineVisual("▲", Colors.ERROR),
    "unresolved": TimelineVisual("?", Colors.TEXT_MUTED),
}


def visual_for(kind: str) -> TimelineVisual:
    """Return a stable timeline visual for one already-classified event kind."""
    return TIMELINE_VISUALS.get(str(kind or "").strip().casefold(), TIMELINE_VISUALS["unresolved"])


def phase_event(*, marker: str, label: str, detail: str = "") -> dict[str, str]:
    """Build a FoundryTimeline event for one explicit persisted phase."""
    visual = visual_for("phase")
    return {
        "marker": f"{visual.symbol} {marker}".strip(),
        "label": label or "Phase",
        "detail": detail,
        "color": visual.color,
    }


def unresolved_event(
    *,
    label: str = "Timeline coverage unresolved",
    detail: str = "No source-backed phase threshold or timing event is persisted for this encounter yet.",
) -> dict[str, str]:
    """Build an explicit unresolved timeline event without inventing timing."""
    visual = visual_for("unresolved")
    return {
        "marker": visual.symbol,
        "label": label,
        "detail": detail,
        "color": visual.color,
    }
