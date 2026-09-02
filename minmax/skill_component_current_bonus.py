from __future__ import annotations

"""Phase 6 semantics for coefficient placeholders that display current stat totals.

These rows do not introduce new runtime math. They explain that ``$N`` is the
current aggregate of an explicit per-unit passive bonus. Build/stat resolution
owns the actual equipped/slotted count and applies the standing stat effect.
"""

import re
from dataclasses import dataclass
from enum import Enum

from .stat_ids import StatId


class SkillComponentCurrentBonusDriver(str, Enum):
    LIGHT_ARMOR_PIECES_EQUIPPED = "light_armor_pieces_equipped"
    HEAVY_ARMOR_PIECES_EQUIPPED = "heavy_armor_pieces_equipped"
    SORCERER_ABILITIES_SLOTTED = "sorcerer_abilities_slotted"
    NIGHTBLADE_ABILITIES_SLOTTED = "nightblade_abilities_slotted"
    WINTERS_EMBRACE_ABILITIES_SLOTTED = "winters_embrace_abilities_slotted"
    HERALD_OF_THE_TOME_ABILITIES_SLOTTED = "herald_of_the_tome_abilities_slotted"
    SOLDIER_OF_APOCRYPHA_ABILITIES_SLOTTED = "soldier_of_apocrypha_abilities_slotted"


class SkillComponentCurrentBonusMode(str, Enum):
    FLAT_PER_UNIT = "flat_per_unit"
    PERCENT_PER_UNIT = "percent_per_unit"


@dataclass(frozen=True)
class SkillComponentCurrentBonus:
    skill_rank_id: int
    coefficient_number: int
    stats: tuple[StatId, ...]
    driver: SkillComponentCurrentBonusDriver
    mode: SkillComponentCurrentBonusMode
    amount_per_unit: float
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.stats:
            raise ValueError("stats must be non-empty")
        if self.amount_per_unit <= 0:
            raise ValueError("amount_per_unit must be positive")
        if not self.evidence:
            raise ValueError("evidence must be non-empty")


_STAT_PHRASES: tuple[tuple[str, tuple[StatId, ...]], ...] = (
    ("health, magicka, and stamina recovery", (StatId.HEALTH_RECOVERY, StatId.MAGICKA_RECOVERY, StatId.STAMINA_RECOVERY)),
    ("physical and spell penetration", (StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION)),
    ("physical and spell resistance", (StatId.PHYSICAL_RESISTANCE, StatId.SPELL_RESISTANCE)),
    ("weapon and spell critical rating", (StatId.WEAPON_CRITICAL, StatId.SPELL_CRITICAL)),
    ("weapon and spell damage", (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE)),
    ("critical chance rating", (StatId.WEAPON_CRITICAL, StatId.SPELL_CRITICAL)),
    ("spell resistance", (StatId.SPELL_RESISTANCE,)),
)

_DRIVER_PATTERNS: tuple[tuple[SkillComponentCurrentBonusDriver, str], ...] = (
    (SkillComponentCurrentBonusDriver.LIGHT_ARMOR_PIECES_EQUIPPED, r"(?:for\s+each|per)\s+piece\s+of\s+light\s+armor\s+(?:equipped|worn)"),
    (SkillComponentCurrentBonusDriver.HEAVY_ARMOR_PIECES_EQUIPPED, r"(?:for\s+each|per)\s+piece\s+of\s+heavy\s+armor\s+equipped"),
    (SkillComponentCurrentBonusDriver.SORCERER_ABILITIES_SLOTTED, r"(?:for\s+each|per)\s+sorcerer\s+ability\s+slotted"),
    (SkillComponentCurrentBonusDriver.NIGHTBLADE_ABILITIES_SLOTTED, r"(?:for\s+each|per)\s+nightblade\s+ability\s+slotted"),
    (SkillComponentCurrentBonusDriver.WINTERS_EMBRACE_ABILITIES_SLOTTED, r"(?:for\s+each|per)\s+winter'?s\s+embrace\s+ability\s+slotted"),
    (SkillComponentCurrentBonusDriver.HERALD_OF_THE_TOME_ABILITIES_SLOTTED, r"(?:for\s+each|per)\s+herald\s+of\s+the\s+tome\s+ability\s+slotted"),
    (SkillComponentCurrentBonusDriver.SOLDIER_OF_APOCRYPHA_ABILITIES_SLOTTED, r"(?:for\s+each|per)\s+soldier\s+of\s+apocrypha\s+ability\s+slotted"),
)


def extract_explicit_component_current_bonus(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentCurrentBonus, ...]:
    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    current = re.search(
        rf"\bcurrent\s+bonus\s*:\s*\${int(coefficient_number)}(?!\d)(?P<pct>\s*%)?",
        text,
        re.IGNORECASE,
    )
    if current is None:
        return ()

    lower = text.casefold()
    stat_match: tuple[str, tuple[StatId, ...]] | None = None
    stat_pos = -1
    for phrase, stats in _STAT_PHRASES:
        pos = lower.find(phrase)
        if pos >= 0 and (stat_pos < 0 or pos < stat_pos):
            stat_match = (phrase, stats)
            stat_pos = pos
    if stat_match is None:
        return ()

    driver: SkillComponentCurrentBonusDriver | None = None
    driver_match: re.Match[str] | None = None
    for candidate, pattern in _DRIVER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match is not None:
            driver = candidate
            driver_match = match
            break
    if driver is None or driver_match is None:
        return ()

    # The literal per-unit amount appears after the stat phrase and before the
    # count driver. Keep this intentionally local so unrelated numbers in the
    # tooltip cannot become passive magnitudes.
    stat_end = stat_pos + len(stat_match[0])
    local = text[stat_end:driver_match.start()]
    amount_match = re.search(r"\bby\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<pct>%)?", local, re.IGNORECASE)
    if amount_match is None:
        return ()

    amount = float(amount_match.group("amount"))
    is_percent = bool(amount_match.group("pct"))
    mode = SkillComponentCurrentBonusMode.PERCENT_PER_UNIT if is_percent else SkillComponentCurrentBonusMode.FLAT_PER_UNIT
    if is_percent:
        amount /= 100.0

    evidence = text[stat_pos:current.end()].strip(" .")
    return (
        SkillComponentCurrentBonus(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            stats=stat_match[1],
            driver=driver,
            mode=mode,
            amount_per_unit=amount,
            evidence=evidence,
        ),
    )
