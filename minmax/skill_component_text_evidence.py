from __future__ import annotations

"""Conservative semantic evidence extracted from coefficient-aware tooltip text.

The UESP-derived ``coef_description`` text is the only text field used here to
associate a coefficient slot with nearby wording. Raw descriptions are useful
corroboration, but their placeholder numbering can differ from coefficient slot
numbering and therefore must not be used as the slot map.

This module extracts evidence. It does not silently turn incomplete wording into
complete combat classification.
"""

import re
from dataclasses import dataclass


_DAMAGE_TYPES = {
    "flame": "flame",
    "frost": "frost",
    "shock": "shock",
    "magic": "magical",
    "physical": "physical",
    "poison": "poison",
    "disease": "disease",
    "bleed": "bleed",
}


@dataclass(frozen=True)
class SkillComponentTextEvidence:
    coefficient_number: int
    fragment: str
    effect_kind: str | None = None
    damage_type: str | None = None
    is_dot: bool | None = None
    is_aoe: bool | None = None
    can_crit: bool | None = None
    evidence: tuple[str, ...] = ()

    @property
    def has_semantic_evidence(self) -> bool:
        return any(
            value is not None
            for value in (
                self.effect_kind,
                self.damage_type,
                self.is_dot,
                self.is_aoe,
                self.can_crit,
            )
        )


def _normalize_text(value: str | None) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    return " ".join(text.split())


def _placeholder_pattern(number: int) -> re.Pattern[str]:
    # UESP coefficient-aware descriptions commonly wrap $N in color markup.
    return re.compile(rf"\${int(number)}(?!\d)")


def _fragment_around_placeholder(text: str, number: int) -> str:
    match = _placeholder_pattern(number).search(text)
    if match is None:
        return ""

    # Sentence boundaries are the safest useful unit. If no punctuation exists,
    # preserve a bounded local window rather than pretending the whole tooltip is
    # mechanically one component.
    start = max(text.rfind(".", 0, match.start()), text.rfind(";", 0, match.start()))
    start = 0 if start < 0 else start + 1

    end_candidates = [
        position
        for position in (
            text.find(".", match.end()),
            text.find(";", match.end()),
        )
        if position >= 0
    ]
    end = min(end_candidates) + 1 if end_candidates else len(text)

    fragment = text[start:end].strip()
    if len(fragment) <= 360:
        return fragment

    local_start = max(0, match.start() - 150)
    local_end = min(len(text), match.end() + 210)
    return text[local_start:local_end].strip()


def extract_component_text_evidence(
    coef_description: str | None,
    coefficient_number: int,
) -> SkillComponentTextEvidence:
    """Extract only explicit mechanics near ``$coefficient_number``.

    Important non-rules:
    - duration alone does not imply DoT;
    - radius alone does not imply AoE;
    - the word ``Area`` in an ability-level target field is not consulted here;
    - critical eligibility is not assumed for damage or healing.
    """

    text = _normalize_text(coef_description)
    fragment = _fragment_around_placeholder(text, coefficient_number)
    if not fragment:
        return SkillComponentTextEvidence(
            coefficient_number=int(coefficient_number),
            fragment="",
        )

    lower = fragment.casefold()
    evidence: list[str] = [f"coef_description contains ${int(coefficient_number)}"]

    effect_kind: str | None = None
    damage_type: str | None = None
    is_dot: bool | None = None
    is_aoe: bool | None = None
    can_crit: bool | None = None

    # Effect kind is accepted only when the fragment explicitly names the
    # outcome. ``Health`` by itself is not enough because max-health and health
    # cost text exist in ESO tooltips. Shield wording is checked before generic
    # Damage because the phrase ``damage shield`` contains the word damage.
    if any(token in lower for token in ("damage shield", "shield that absorbs", "absorbs ")):
        effect_kind = "shield"
        evidence.append("fragment explicitly describes a damage shield")
    elif " damage" in lower:
        effect_kind = "damage"
        evidence.append("fragment explicitly says Damage")
    elif any(token in lower for token in ("healing ", "heal ", "heals ", "restore ")) and "health" in lower:
        effect_kind = "heal"
        evidence.append("fragment explicitly describes healing/restoring Health")

    if effect_kind == "damage":
        for token, canonical in _DAMAGE_TYPES.items():
            if re.search(rf"\b{re.escape(token)}\s+damage\b", lower):
                damage_type = canonical
                evidence.append(f"fragment explicitly says {token.title()} Damage")
                break

        periodic_patterns = (
            r"\bevery\s+(?:\d+(?:\.\d+)?\s+)?seconds?\b",
            r"\bper\s+seconds?\b",
            r"\beach\s+seconds?\b",
            r"\bdamage\s+over\s+\d+(?:\.\d+)?\s+seconds?\b",
        )
        if any(re.search(pattern, lower) for pattern in periodic_patterns):
            is_dot = True
            evidence.append("fragment explicitly describes periodic/over-time damage")
        elif any(phrase in lower for phrase in ("dealing", "deal ", "deals ")):
            # Explicit one-shot wording can establish direct only when no
            # periodic wording is present in the same component fragment.
            is_dot = False
            evidence.append("fragment describes a damage event without periodic wording")

        aoe_patterns = (
            r"\ball enemies in (?:the|an) area\b",
            r"\bnearby enemies\b",
            r"\benemies in the (?:target )?area\b",
            r"\bto all enemies\b",
        )
        if any(re.search(pattern, lower) for pattern in aoe_patterns):
            is_aoe = True
            evidence.append("fragment explicitly describes multiple/area enemies")
        elif any(phrase in lower for phrase in ("an enemy", "the enemy", "target enemy")):
            is_aoe = False
            evidence.append("fragment explicitly describes one enemy")

    elif effect_kind == "heal":
        if any(phrase in lower for phrase in ("you and your allies", "allies in", "nearby allies", "all allies")):
            is_aoe = True
            evidence.append("fragment explicitly describes multiple allies")
        elif any(phrase in lower for phrase in ("an ally", "target ally")):
            is_aoe = False
            evidence.append("fragment explicitly describes one ally")

        if any(re.search(pattern, lower) for pattern in (
            r"\bevery\s+(?:\d+(?:\.\d+)?\s+)?seconds?\b",
            r"\bheal(?:ing|s)?\s+over\s+\d+(?:\.\d+)?\s+seconds?\b",
        )):
            is_dot = True
            evidence.append("fragment explicitly describes periodic healing")
        else:
            is_dot = False
            evidence.append("fragment describes an immediate heal without periodic wording")

    # ESO critical eligibility is deliberately unresolved here. Tooltip prose
    # usually does not prove whether an effect can crit.

    return SkillComponentTextEvidence(
        coefficient_number=int(coefficient_number),
        fragment=fragment,
        effect_kind=effect_kind,
        damage_type=damage_type,
        is_dot=is_dot,
        is_aoe=is_aoe,
        can_crit=can_crit,
        evidence=tuple(evidence),
    )
