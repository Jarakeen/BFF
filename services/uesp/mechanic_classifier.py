from __future__ import annotations

"""Conservative interpretation of UESP encounter ability descriptions.

The classifier extracts source-supported behavioral facts. It does not invent
raid execution strategy. Strategy remains a separate curated layer.
"""
import re
from dataclasses import dataclass
from typing import Optional


MECHANIC_TYPES = {
    "attack",
    "area_attack",
    "targeted_attack",
    "targeted_hazard",
    "hazard",
    "movement",
    "positioning",
    "cleanse",
    "interrupt",
    "charge",
    "summon",
    "add_spawn",
    "phase_transition",
    "resource",
    "stack",
    "spread",
    "environment",
}


@dataclass
class MechanicClassification:
    mechanic_type: Optional[str] = None
    damage_type: Optional[str] = None
    target_count: Optional[int] = None
    requires_movement: Optional[bool] = None
    requires_positioning: Optional[bool] = None
    requires_cleanse: Optional[bool] = None
    persistent_hazard: Optional[bool] = None
    failure_is_fatal: Optional[bool] = None
    interruptible: Optional[bool] = None
    interrupt_note: str = ""
    interpretation_status: str = "inferred"


_COUNT_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


def _has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def _first_damage_type(text: str) -> Optional[str]:
    """Identify damage types only when the prose attributes them to the attack."""
    patterns = [
        ("flame", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bflame damage\b"),
        ("frost", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bfrost damage\b"),
        ("shock", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bshock damage\b"),
        ("poison", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bpoison damage\b"),
        ("disease", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bdisease damage\b"),
        ("physical", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bphysical damage\b"),
        ("magic", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bmagical damage\b"),
        ("bleed", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\bbleed(?: damage)?\b"),
        ("oblivion", r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b[^.]{0,100}\boblivion damage\b"),
    ]
    for damage_type, pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return damage_type
    return None


def classify_mechanic(name: str, description: str) -> MechanicClassification:
    text = f"{name} {description}".lower()

    count_match = re.search(
        r"\b(one|two|three|four|five|six|1|2|3|4|5|6)\b"
        r"(?:\s+\w+){0,3}\s+(?:targets?|players?|party members?)\b",
        text,
    )
    target_count = None
    if count_match:
        token = count_match.group(1)
        target_count = _COUNT_WORDS.get(token, int(token) if token.isdigit() else None)

    requires_cleanse = _has(text, r"\bcleanse\b|\bcleanses\b|\bpurge\b")
    persistent_hazard = _has(
        text,
        r"\blingering\b|\bpersistent\b|\bdrop .*pools?\b|\bcracked earth\b|\barea .* remains\b|\bremains .* area\b",
    )
    requires_movement = _has(
        text,
        r"\bdodge\b|\bdodged\b|\bwalk(?:ing)? into\b|\bmove out\b|\bmove away\b|\bavoid\b|\bpath\b|\brun through\b|\bmove through\b|\bmoving walls?\b",
    )
    requires_positioning = _has(
        text,
        r"\bfarthest\b|\baway from\b|\bcorners?\b|\boutside\b|\bspread\b|\bstanding\b",
    )
    spread = _has(
        text,
        r"\bspread\b|\bswirls? away\b|\bnearby players?\b|\btransfers? the curse\b",
    )
    failure_is_fatal = _has(
        text,
        r"\bfatal\b|\bkills? (?:the|a|all) player|\bdie(?:s)?\b",
    )

    interruptible = None
    interrupt_note = ""
    if _has(text, r"\bcan be interrupted\b|\bcan be interruptible\b|\binterruptible\b"):
        interruptible = True
        interrupt_note = "UESP description indicates the ability can be interrupted."

    area_attack = _has(
        text,
        r"\barea\b|\baoe\b|\bexplod(?:e|es|ing|ed)\b|\btrails?\b|\bmeteors?\b|\bsalvo\b|\bblast\b|\bcircle\b|\btornadoes?\b|\bflaming walls?\b",
    )
    charge = _has(text, r"\bcharges?\b|\bcharge forward\b")
    summon = _has(text, r"\bsummon\b|\bsummons\b|\bspawn(?:s|ed)?\b|\bcalled forth\b")
    meaningful_summon = summon and _has(
        text,
        r"\bhealth thresholds?\b|\bat \d+% health\b|\b(?:if|when) .* reaches?\b|\bfrom the .* portal\b|\bfall from the sky\b|\bappears?\b|\benters? the fight\b|\benrage\b|\bempower\b|\bmust be\b|\bshould be\b|\bif .* absorbed\b|\bif .* allowed\b",
    )

    mechanic_type: Optional[str] = None
    if target_count is not None and persistent_hazard:
        mechanic_type = "targeted_hazard"
    elif requires_cleanse:
        mechanic_type = "cleanse"
    elif interruptible:
        mechanic_type = "interrupt"
    elif charge:
        mechanic_type = "charge"
    elif meaningful_summon:
        mechanic_type = "summon"
    elif persistent_hazard:
        mechanic_type = "hazard"
    elif spread:
        mechanic_type = "spread"
    elif target_count is not None and requires_positioning:
        mechanic_type = "targeted_attack"
    elif requires_positioning:
        mechanic_type = "positioning"
    elif area_attack:
        mechanic_type = "area_attack"
    elif requires_movement:
        mechanic_type = "movement"

    return MechanicClassification(
        mechanic_type=mechanic_type,
        damage_type=_first_damage_type(text),
        target_count=target_count,
        requires_movement=requires_movement or None,
        requires_positioning=requires_positioning or None,
        requires_cleanse=requires_cleanse or None,
        persistent_hazard=persistent_hazard or None,
        failure_is_fatal=failure_is_fatal or None,
        interruptible=interruptible,
        interrupt_note=interrupt_note,
        interpretation_status="inferred",
    )
