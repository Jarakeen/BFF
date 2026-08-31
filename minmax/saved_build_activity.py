from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild

from .build_sustain import NamedBuildAction


@dataclass(frozen=True)
class SavedBarActivityPlan:
    """Deterministic action sequence derived from one saved ESO ability bar.

    This is an audit/integration plan, not a claimed optimal rotation. ESO saved
    bars contain five ordinary skill slots followed by one Ultimate slot. Phase 4
    sustain currently models primary resources only, so the Ultimate slot is
    deliberately excluded from this planner.
    """

    active_bar: str
    duration_seconds: float
    action_interval_seconds: float
    actions: tuple[NamedBuildAction, ...]


def create_saved_bar_activity_plan(
    build: PlayerBuild,
    *,
    active_bar: str = "front",
    duration_seconds: float = 20.0,
    first_action_seconds: float = 1.0,
    action_interval_seconds: float = 1.0,
) -> SavedBarActivityPlan:
    """Repeat the five ordinary saved bar slots through a fixed time window.

    Empty slots are ignored. The sixth saved slot is the Ultimate and is excluded
    because this Phase 4 integration slice evaluates Health/Magicka/Stamina
    sustain only. The resulting plan is deterministic and intentionally makes no
    claims about skill duration, priority, weaving, or optimal rotation.
    """

    bar = str(active_bar or "front").strip().casefold()
    if bar not in {"front", "back"}:
        raise ValueError("active_bar must be 'front' or 'back'")

    duration = float(duration_seconds)
    first = float(first_action_seconds)
    interval = float(action_interval_seconds)
    if duration < 0:
        raise ValueError("activity duration cannot be negative")
    if first < 0:
        raise ValueError("first action time cannot be negative")
    if interval <= 0:
        raise ValueError("action interval must be positive")

    saved = build.BackBarSkills if bar == "back" else build.FrontBarSkills
    ordinary_skills = tuple(
        str(name or "").strip()
        for name in tuple(saved)[:5]
        if str(name or "").strip()
    )

    actions: list[NamedBuildAction] = []
    if ordinary_skills:
        index = 0
        time_seconds = first
        while time_seconds <= duration:
            actions.append(
                NamedBuildAction(
                    time_seconds=time_seconds,
                    skill_name=ordinary_skills[index % len(ordinary_skills)],
                )
            )
            index += 1
            time_seconds = first + (index * interval)

    return SavedBarActivityPlan(
        active_bar=bar,
        duration_seconds=duration,
        action_interval_seconds=interval,
        actions=tuple(actions),
    )
