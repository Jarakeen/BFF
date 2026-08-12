# models/uesp_models.py
"""Structured data models for the local UESP knowledge base."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UespSource:
    url: str
    page_title: str
    revision_id: int | None = None
    retrieved_at: str = ""
    license: str = "CC BY-SA 2.5 (UESP)"


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
    name: str
    description: str = ""
    links: list[str] = field(default_factory=list)


@dataclass
class UespPhase:
    label: str
    threshold: str = ""
    description: str = ""


@dataclass
class UespDialogueLine:
    speaker: str
    line: str
    trigger: str = ""
    ability: str | None = None


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


@dataclass
class UespContent:
    id: str
    name: str
    content_type: str
    summary: str = ""
    location: str = ""
    boss_ids: list[str] = field(default_factory=list)
    achievements: list[UespAchievement] = field(default_factory=list)
    related_npcs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source: UespSource | None = None
