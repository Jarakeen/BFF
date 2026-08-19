# models/uesp_models.py
"""Structured source data models for the local UESP knowledge base."""

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
    damage_type: str | None = None


@dataclass
class UespMechanic:
    """A source-described or conservatively inferred encounter mechanic.

    ``interpretation_status`` distinguishes UESP/source facts from later
    curated strategy annotations. This model intentionally stores the raw
    ability description alongside the classification so the optimizer can
    trace a conclusion back to source text.
    """

    description: str
    name: str = ""
    links: list[str] = field(default_factory=list)
    mechanic_type: str | None = None
    damage_type: str | None = None
    target_count: int | None = None
    requires_movement: bool | None = None
    requires_positioning: bool | None = None
    requires_cleanse: bool | None = None
    persistent_hazard: bool | None = None
    failure_is_fatal: bool | None = None
    interruptible: bool | None = None
    interrupt_note: str = ""
    interpretation_status: str = "source"


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

    group_size: int | None = None

    boss_ids: list[str] = field(default_factory=list)

    achievements: list[UespAchievement] = field(default_factory=list)

    # Eventually:
    set_ids: list[str] = field(default_factory=list)
    reward_ids: list[str] = field(default_factory=list)

    related_npcs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    source: UespSource | None = None
