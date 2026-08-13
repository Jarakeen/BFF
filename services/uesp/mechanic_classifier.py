from __future__ import annotations

"""Conservative interpretation of UESP encounter ability descriptions.

The classifier extracts source-supported behavioral facts. It does not invent
raid execution strategy. Strategy remains a separate curated layer.
"""

from dataclasses import dataclass
import re
from typing import Optional


MECHANIC_TYPES = {
    "attack",
    "area_attack",
    "targeted_attack",
    "hazard",
    "movement",
    "positioning",
    "cleanse",
    "interrupt",
    "summon",
    "add_spawn",
    "phase_transition",
    "resource",
    "stack",
    "spread",
    "environment",
}


@dataclass(frozen=True)
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


_DAMAGE_PATTERNS = {
    "poison": r"\bpoison\b|poisonous|noxious",
    "flame": r"\bflame\b|fire|fiery|burn",
    "physical": r"\bphysical\b|chomp|smash|stomp|crush",
    "frost": r"\bfrost\b|ice|icy|freeze",
    "shock": r"\bshock\b|lightning|electric",
}

_COUNT_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


def classify_mechanic(name: str, description: str) -> MechanicClassification:
    text = f"{name} {description}".lower()

    damage_type = _first_damage_type(text)

    target_count = None
    count_match = re.search(
        r"\b(one|two|three|four|five|six|1|2|3|4|5|6)\s+targets?\b", text
    )
    if count_match:
        token = count_match.group(1)
        target_count = _COUNT_WORDS.get(token, int(token) if token.isdigit() else None)

    requires_cleanse = _has(
        text, r"\bcleanse\b|\bcleanses\b|\bcleanse the effect\b|\bpurge\b"
    )
    persistent_hazard = _has(
        text,
        r"\blingering\b|\bpersistent\b|\bdrop .*pools?\b|\bpool\b|\bhazard\b|\bcracked earth\b",
    )
    requires_movement = _has(
        text, r"\bdodge\b|\bdodged\b|\bcharge\b|\bwalk(?:ing)? into\b|\bmove\b|\bmovement\b|\bpath\b"
    )
    requires_positioning = _has(
        text,
        r"\bfarthest\b|\bposition\b|\bstanding\b|\brange\b|\bnear\b|\baway from\b|\bcorners?\b|\btarget area\b",
    )

    interruptible = None
    interrupt_note = ""
    if re.search(r"\binterruptible\b|\bcan be interrupted\b", text):
        interruptible = True
        interrupt_note = "UESP description indicates the ability can be interrupted."

    summon = _has(text, r"\bsummon\b|\bsummons\b|\bspawn(?:s|ed)?\b|\bcalled forth\b")
    area_attack = _has(
        text,
        r"\barea\b|\baoe\b|\bexploding\b|\btrails?\b|\bmeteors?\b|\bsalvo\b|\bblast\b|\bcircle\b",
    )

    mechanic_type: Optional[str] = None
    if requires_cleanse:
        mechanic_type = "cleanse"
    elif summon:
        mechanic_type = "summon"
    elif persistent_hazard:
        mechanic_type = "hazard"
    elif interruptible:
        mechanic_type = "interrupt"
    elif requires_positioning and target_count is not None:
        mechanic_type = "targeted_attack"
    elif requires_positioning:
        mechanic_type = "positioning"
    elif area_attack:
        mechanic_type = "area_attack"
    elif requires_movement:
        mechanic_type = "movement"

    return MechanicClassification(
        mechanic_type=mechanic_type,
        damage_type=damage_type,
        target_count=target_count,
        requires_movement=requires_movement,
        requires_positioning=requires_positioning,
        requires_cleanse=requires_cleanse,
        persistent_hazard=persistent_hazard,
        failure_is_fatal=None,
        interruptible=interruptible,
        interrupt_note=interrupt_note,
    )


def _first_damage_type(text: str) -> Optional[str]:
    """Return a damage type only when the description contains explicit cues."""
    for candidate, pattern in _DAMAGE_PATTERNS.items():
        if re.search(pattern, text):
            return candidate
    return None


def _has(text: str, pattern: str) -> Optional[bool]:
    return True if re.search(pattern, text) else None
