# models/uesp_models.py
"""
Structured data models for the local UESP knowledge base
(data/uesp/). These are intentionally separate from models/boss.py:
that module describes the app's own archive-run format (numbers a
streamer fills in while running a trial), while these describe facts
*sourced from* UESP, each one traceable back to a specific wiki page,
revision, and retrieval date.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------
# Provenance
# --------------------------------------------------

@dataclass
class UespSource:
    """Where a record came from and when it was fetched."""

    url: str
    page_title: str
    revision_id: int | None = None
    retrieved_at: str = ""  # ISO-8601 UTC timestamp
    license: str = "CC BY-SA 2.5 (UESP)"


# --------------------------------------------------
# Boss-level structures
# --------------------------------------------------

@dataclass
class UespHealth:
    normal: str = ""
    veteran: str = ""
    hardmode: str = ""


@dataclass
class UespAbility:
    name: str
    description: str = ""

@dataclass
class UespMechanic:
    description: str
    links: list[str] = field(default_factory=list)


@dataclass
class UespPhase:
    label: str
    threshold: str = ""  # raw text as found, e.g. "70%"
    description: str = ""


@dataclass
class UespDialogueLine:
    speaker: str
    line: str
    trigger: str = ""  # nearby context text, e.g. "At 70%:"
    ability: str | None = None  # matched ability name when evidence is sufficient


@dataclass
class UespAchievement:
    id: str
    name: str
    description: str = ""
    points: int | None = None
    source: UespSource | None = None


@dataclass
class UespDifficultyNotes:
    normal_veteran_differences: list[str] = field(default_factory=list)
    hardmode_info: list[str] = field(default_factory=list)


@dataclass
class UespBoss:
    id: str
    name: str
    content_id: str = ""
    content_name: str = ""
    location: str = ""
    species: str = ""
    reaction: str = ""
    health: UespHealth = field(default_factory=UespHealth)
    abilities: list[UespAbility] = field(default_factory=list)
    mechanics: list[UespMechanic] = field(default_factory=list)
    phases: list[UespPhase] = field(default_factory=list)
    dialogue: list[UespDialogueLine] = field(default_factory=list)
    dialogue_by_trigger: dict[str, list[UespDialogueLine]] = field(default_factory=dict)
    achievements: list[UespAchievement] = field(default_factory=list)
    difficulty_notes: UespDifficultyNotes = field(default_factory=UespDifficultyNotes)
    strategy_notes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    related_npcs: list[str] = field(default_factory=list)
    related_quests: list[str] = field(default_factory=list)
    summary: str = ""
    source: UespSource | None = None

# --------------------------------------------------
# Content-level structures (trial / dungeon / arena)
# --------------------------------------------------

@dataclass
class UespContent:
    id: str  # stable slug, e.g. "rockgrove"
    name: str
    content_type: str  # "trial" | "dungeon" | "arena"

    summary: str = ""
    location: str = ""

    boss_ids: list[str] = field(default_factory=list)
    achievements: list[UespAchievement] = field(default_factory=list)
    related_npcs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    source: UespSource | None = None
