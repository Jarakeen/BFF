from __future__ import annotations

"""Conservative rule-based classification of UESP encounter mechanics.

This layer deliberately classifies only facts that are reasonably supported by
UESP ability descriptions. Raid execution strategies remain separate and are
never inferred here.
"""

from dataclasses import dataclass
import re
from typing import Optional


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


def classify_mechanic(name: str, description: str) -> MechanicClassification:
    text = f"{name} {description}".lower()

    damage_type = None
    for candidate, pattern in _DAMAGE_PATTERNS.items():
        if re.search(pattern, text):
            damage_type = candidate
            break

    target_count = None
    count_match = re.search(r"\b(one|two|three|four|five|six|1|2|3|4|5|6)\s+targets?\b", text)
    if count_match:
        target_count = {
            "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6,
        }.get(count_match.group(1), int(count_match.group(1)) if count_match.group(1).isdigit() else None)

    requires_cleanse = bool(re.search(r"\bcleanse|cleanses|cleanse the effect|purge\b", text)) or None
    persistent_hazard = bool(re.search(r"\blingering\b|\bpersistent\b|\bdrop .*pools?\b|\bpool\b|\bhazard\b", text)) or None
    requires_movement = bool(re.search(r"\bdodge|dodged|charge|walk(?:ing)? into|move|movement|path\b", text)) or None
    requires_positioning = bool(re.search(r"\bfarthest\b|\bposition|standing|range|near|away from|corners?\b", text)) or None

    interruptible = None
    interrupt_note = ""
    if re.search(r"\binterruptible\b|\bcan be interrupted\b", text):
        interruptible = True
        interrupt_note = "UESP description indicates the ability can be interrupted."
    elif re.search(r"\binterrupt\b|\binterrupts?\b", text):
        interruptible = True
        interrupt_note = "UESP description references interruption."

    mechanic_type = None
    if requires_cleanse:
        mechanic_type = "cleanse"
    elif persistent_hazard:
        mechanic_type = "hazard"
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
