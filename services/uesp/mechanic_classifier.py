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
    """
    Identify damage types when the description actually attributes
    that damage to the ability or its affected targets.
    """

    patterns = [
        (
            "flame",
            r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b"
            r"[^.]{0,100}\bflame damage\b",
        ),
        (
            "frost",
            r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b"
            r"[^.]{0,100}\bfrost damage\b",
        ),
        (
            "poison",
            r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b"
            r"[^.]{0,100}\bpoison damage\b",
        ),
        (
            "poison",
            r"\bpoisoned targets?\b[^.]{0,100}\bpoison damage\b",
        ),
        (
            "poison",
            r"\bpoisoned players?\b[^.]{0,100}\bpoison damage\b",
        ),
        (
            "physical",
            r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b"
            r"[^.]{0,100}\bphysical damage\b",
        ),
        (
            "magic",
            r"\b(?:dealing|deals|deal|inflicts|causing|causes)\b"
            r"[^.]{0,100}\bmagical damage\b",
        ),
    ]

    for damage_type, pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return damage_type

    return None


def classify_mechanic(name: str, description: str) -> MechanicClassification:
    text = f"{name} {description}".lower()

    # ---------------------------------------------------------
    # Target count
    # ---------------------------------------------------------

    target_count = None

    count_match = re.search(
        r"\b(one|two|three|four|five|six|1|2|3|4|5|6)\b"
        r"(?:\s+\w+){0,3}\s+"
        r"(?:targets?|players?|party members?)\b",
        text,
    )

    if count_match:
        token = count_match.group(1)
        target_count = _COUNT_WORDS.get(
            token,
            int(token) if token.isdigit() else None,
        )

    # ---------------------------------------------------------
    # Explicit mechanics
    # ---------------------------------------------------------

    requires_cleanse = _has(
        text,
        r"\bcleanse\b|\bcleanses\b|\bcleanse the effect\b|\bpurge\b",
    )

    persistent_hazard = _has(
        text,
        r"\blingering\b"
        r"|\bpersistent\b"
        r"|\bdrop .*pools?\b"
        r"|\bcracked earth\b"
        r"|\barea .* remains\b"
        r"|\bremains .* area\b",
    )

    requires_movement = _has(
        text,
        r"\bdodge\b"
        r"|\bdodged\b"
        r"|\bwalk(?:ing)? into\b"
        r"|\bmove out\b"
        r"|\bmove away\b"
        r"|\bavoid\b"
        r"|\bpath\b"
        r"|\brun through\b"
        r"|\bmove through\b"
        r"|\bmoving walls?\b"
        r"|\bmoving walls? of\b",
    )

    requires_positioning = _has(
        text,
        r"\bfarthest\b"
        r"|\baway from\b"
        r"|\bcorners?\b"
        r"|\boutside\b"
        r"|\bspread\b"
        r"|\bstanding\b",
    )


    spread = _has(
    text,
        r"\bspread\b"
        r"|\bswirls? away\b"
        r"|\bnearby players?\b"
        r"|\btransfers? the curse\b",
    )
    # ---------------------------------------------------------
    # Interrupt
    #
    # Only trust explicit UESP wording.
    # ---------------------------------------------------------

    interruptible = None
    interrupt_note = ""

    if re.search(
        r"\bcan be interrupted\b|\bcan be interruptible\b|\binterruptible\b",
        text,
        re.IGNORECASE,
    ):
        interruptible = True
        interrupt_note = (
            "UESP description indicates the ability can be interrupted."
        )

    # ---------------------------------------------------------
    # Area attacks
    # ---------------------------------------------------------

    area_attack = _has(
        text,
        r"\barea\b"
        r"|\baoe\b"
        r"|\bexplod(?:e|es|ing|ed)\b"
        r"|\btrails?\b"
        r"|\bmeteors?\b"
        r"|\bsalvo\b"
        r"|\bblast\b"
        r"|\bcircle\b"
        r"|\btornadoes?\b"
        r"|\bflaming walls?\b",
    )

    # ---------------------------------------------------------
    # Charges
    # ---------------------------------------------------------

    charge = _has(
        text,
        r"\bcharges?\b|\bcharge forward\b",
    )

    # ---------------------------------------------------------
    # Summons
    #
    # A summon is only useful as a mechanic when the description
    # actually tells us something meaningful happens because of it.
    #
    # "Occasionally, Death Hoppers are summoned..."
    # is technically a summon, but contains no actionable mechanic.
    # ---------------------------------------------------------

    summon = _has(
        text,
        r"\bsummon\b|\bsummons\b|\bspawn(?:s|ed)?\b|\bcalled forth\b",
    )

    meaningful_summon = summon and (
        _has(
            text,
            r"\bhealth thresholds?\b"
            r"|\bat \d+% health\b"
            r"|\bfrom the .* portal\b"
            r"|\bfall from the sky\b"
            r"|\bappears?\b"
            r"|\benters? the fight\b"
            r"|\benrage\b"
            r"|\bempower\b"
            r"|\bmust be\b"
            r"|\bshould be\b"
            r"|\bif .* reaches\b"
            r"|\bif .* absorbed\b"
            r"|\bif .* allowed\b",
        )
    )

    # ---------------------------------------------------------
    # Mechanic type
    #
    # Order matters.
    # ---------------------------------------------------------

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

    elif target_count is not None and requires_positioning:
        mechanic_type = "targeted_attack"

    elif requires_positioning:
        mechanic_type = "positioning"

    elif area_attack:
        mechanic_type = "area_attack"

    elif requires_movement:
        mechanic_type = "movement"

    elif spread:
        mechanic_type = "spread"    

    # ---------------------------------------------------------
    # Do not classify generic basic attacks as mechanics.
    # ---------------------------------------------------------

    if mechanic_type is None:
        return MechanicClassification(
            mechanic_type=None,
            damage_type=None,
            target_count=target_count,
            requires_movement=requires_movement or None,
            requires_positioning=requires_positioning or None,
            requires_cleanse=requires_cleanse or None,
            persistent_hazard=persistent_hazard or None,
            failure_is_fatal=None,
            interruptible=interruptible,
            interrupt_note=interrupt_note,
            interpretation_status="inferred",
        )

    return MechanicClassification(
        mechanic_type=mechanic_type,
        damage_type=_first_damage_type(text),
        target_count=target_count,
        requires_movement=requires_movement or None,
        requires_positioning=requires_positioning or None,
        requires_cleanse=requires_cleanse or None,
        persistent_hazard=persistent_hazard or None,
        failure_is_fatal=None,
        interruptible=interruptible,
        interrupt_note=interrupt_note,
        interpretation_status="inferred",
    )
