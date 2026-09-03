from __future__ import annotations

"""Visual vocabulary for the Mechanics boss timeline.

The timeline receives source-backed encounter events from services. This module
only chooses presentation semantics for already-classified event kinds; it does
not infer mechanics, timing, player strategy, or severity from prose.
"""

from dataclasses import dataclass
from typing import Any

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


def _title_from_key(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title() or "Timeline Event"


def _source_detail(payload: dict[str, Any], evidence_count: int) -> str:
    description = str(payload.get("description") or payload.get("detail") or "").strip()
    source_text = f"Reviewed canonical fact supported by {max(int(evidence_count), 0)} evidence row(s)."
    return f"{description} {source_text}".strip() if description else source_text


def reviewed_timeline_events(
    *,
    canonical_kind: str,
    fact_key: str,
    payload: dict[str, Any],
    evidence_count: int,
) -> list[dict[str, str]]:
    """Render one reviewed canonical phase/transition fact without inference.

    Only explicit trigger fields already present in the canonical payload are
    used. A transition containing several health thresholds becomes one event
    per threshold so the visual timeline preserves each explicit trigger.
    """
    kind = str(canonical_kind or "").strip().casefold()
    payload = dict(payload or {})
    detail = _source_detail(payload, evidence_count)

    if kind == "phase":
        marker = str(payload.get("starts_at") or payload.get("threshold") or "?").strip()
        label = str(payload.get("label") or payload.get("name") or _title_from_key(fact_key)).strip()
        return [phase_event(marker=marker, label=label, detail=detail)]

    if kind == "phase_transition":
        raw_thresholds = payload.get("thresholds")
        if isinstance(raw_thresholds, (list, tuple)):
            thresholds = [str(value).strip() for value in raw_thresholds if str(value).strip()]
        else:
            single = str(payload.get("threshold") or payload.get("starts_at") or "").strip()
            thresholds = [single] if single else []

        label = str(payload.get("label") or payload.get("name") or _title_from_key(fact_key)).strip()
        if thresholds:
            return [phase_event(marker=threshold, label=label, detail=detail) for threshold in thresholds]
        return [
            unresolved_event(
                label=label,
                detail=(
                    f"Reviewed canonical transition has no explicit displayable trigger. {detail}"
                ).strip(),
            )
        ]

    return [
        unresolved_event(
            label=_title_from_key(fact_key),
            detail="Reviewed timeline fact has an unsupported canonical kind for display.",
        )
    ]


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
