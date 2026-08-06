# ==================================================
# Black Feather Foundry
#
# File:
# models/achievement_run_model.py
#
# Purpose:
# Defines an Achievement Run.
#
# ==================================================

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class AchievementItem:
    name: str = ""
    in_progress: bool = False
    complete: bool = False


@dataclass
class AchievementRunModel:
    run_number: str = ""

    date: str = ""

    content: str = ""

    group_size: int = 4

    difficulty: list[str] = field(default_factory=list)

    run_type: list[str] = field(default_factory=list)

    achievements: list[AchievementItem] = field(default_factory=list)

    notes: str = ""

    lessons: str = ""

    next_steps: str = ""

    result: str = ""

    final_time: str = ""

    def to_dict(self) -> dict:
        return asdict(self)