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

_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_ANY_PLACEHOLDER_RE = re.compile(r"\$\d+(?!\d)")


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
    text = _COLOR_TAG_RE.sub("", text)
    return " ".join(text.split())


def _placeholder_pattern(number: int) -> re.Pattern[str]:
    return re.compile(rf"\${int(number)}(?!\d)")


def _fragment_around_placeholder(text: str, number: int) -> str:
    match = _placeholder_pattern(number).search(text)
    if match is None:
        return ""

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


def _component_segment(fragment: str, coefficient_number: int) -> str:
    """Return the clause owned by ``$N`` without borrowing later coefficients.

    The segment starts after the previous coefficient placeholder, if any, and
    ends before the next coefficient placeholder, if any. This prevents wording
    such as ``$2 Damage over 10 seconds`` from incorrectly making ``$1`` a DoT.
    """

    match = _placeholder_pattern(coefficient_number).search(fragment)
    if match is None:
        return ""

    placeholders = list(_ANY_PLACEHOLDER_RE.finditer(fragment))
    current_index = next(
        (index for index, item in enumerate(placeholders) if item.start() == match.start()),
        None,
    )
    if current_index is None:
        return fragment

    start = 0 if current_index == 0 else placeholders[current_index - 1].end()
    end = len(fragment) if current_index + 1 >= len(placeholders) else placeholders[current_index + 1].start()
    return fragment[start:end].strip()


def _placeholder_effect_kind(lower: str, coefficient_number: int) -> str | None:
    """Resolve effect kind only when wording ties the mechanic to ``$N``."""

    placeholder = rf"\${int(coefficient_number)}(?!\d)"

    shield_patterns = (
        rf"(?:damage\s+shield[^.;]{{0,90}}?(?:absorbs?|absorb(?:ing)?)[^.;]{{0,30}}?){placeholder}(?:\s+damage)?\b",
        rf"(?:shield[^.;]{{0,90}}?(?:absorbs?|absorb(?:ing)?)[^.;]{{0,30}}?){placeholder}(?:\s+damage)?\b",
        rf"(?:absorbs?|absorb(?:ing)?)\s+(?:up\s+to\s+)?{placeholder}(?:\s+damage)?\b",
        rf"\bshield(?:ing|s|ed)?\b[^.;]{{0,80}}?\bfor\s+{placeholder}\b",
    )
    if any(re.search(pattern, lower) for pattern in shield_patterns):
        return "shield"

    heal_patterns = (
        rf"\bheal(?:ing|s|ed)?\b[^.;]{{0,70}}?{placeholder}(?:\s+health)?\b",
        rf"\brestore(?:s|d|ing)?\b[^.;]{{0,70}}?{placeholder}\s+health\b",
        rf"{placeholder}\s+health\b[^.;]{{0,45}}?\bheal(?:ing|s|ed)?\b",
        rf"\bsiphon(?:s|ed|ing)?\s+{placeholder}\s+health\b",
    )
    if any(re.search(pattern, lower) for pattern in heal_patterns):
        return "heal"

    damage_type_group = "|".join(re.escape(token) for token in _DAMAGE_TYPES)
    damage_patterns = (
        rf"{placeholder}\s+(?:{damage_type_group})\s+damage\b",
        rf"\b(?:deal(?:ing|s)?|take(?:s|n)?|inflict(?:ing|s)?|hit(?:s|ting)?|blast(?:s|ing)?)\b[^.;]{{0,80}}?{placeholder}\s+damage\b",
    )
    if any(re.search(pattern, lower) for pattern in damage_patterns):
        return "damage"

    return None


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
    component_lower = _component_segment(fragment, coefficient_number).casefold()
    evidence: list[str] = [f"coef_description contains ${int(coefficient_number)}"]

    effect_kind = _placeholder_effect_kind(lower, coefficient_number)
    damage_type: str | None = None
    is_dot: bool | None = None
    is_aoe: bool | None = None
    can_crit: bool | None = None

    if effect_kind == "shield":
        evidence.append("placeholder is explicitly the damage-shield absorb amount")
    elif effect_kind == "heal":
        evidence.append("placeholder is explicitly the healing/restored-Health amount")
    elif effect_kind == "damage":
        evidence.append("placeholder is explicitly the damage amount")

    if effect_kind == "damage":
        placeholder = rf"\${int(coefficient_number)}(?!\d)"
        for token, canonical in _DAMAGE_TYPES.items():
            if re.search(rf"{placeholder}\s+{re.escape(token)}\s+damage\b", lower):
                damage_type = canonical
                evidence.append(f"placeholder explicitly precedes {token.title()} Damage")
                break

        periodic_patterns = (
            r"\bevery\s+(?:\d+(?:\.\d+)?\s+)?seconds?\b",
            r"\bper\s+seconds?\b",
            r"\beach\s+seconds?\b",
            r"\bdamage\s+over\s+\d+(?:\.\d+)?\s+seconds?\b",
        )
        if any(re.search(pattern, component_lower) for pattern in periodic_patterns):
            is_dot = True
            evidence.append("current coefficient explicitly describes periodic/over-time damage")
        else:
            is_dot = False
            evidence.append("current coefficient is a damage event without periodic wording")

        aoe_patterns = (
            r"\ball enemies in (?:the|an) area\b",
            r"\ball enemies hit\b",
            r"\bnearby enemies\b",
            r"\benemies near you\b",
            r"\benemies around (?:you|them|the target)\b",
            r"\bfoes around you\b",
            r"\benemies in the (?:target )?area\b",
            r"\bto all enemies\b",
            r"\bblast(?:s|ing)? all enemies\b",
        )
        if any(re.search(pattern, lower) for pattern in aoe_patterns):
            is_aoe = True
            evidence.append("fragment explicitly describes multiple/area enemies")
        elif any(
            phrase in lower
            for phrase in (
                "an enemy",
                "the enemy",
                "target enemy",
                "your foe",
                "the target",
            )
        ):
            is_aoe = False
            evidence.append("fragment explicitly describes one enemy/target")

    elif effect_kind == "heal":
        if any(
            phrase in lower
            for phrase in (
                "you and your allies",
                "allies in the area",
                "allies in",
                "nearby allies",
                "all allies",
            )
        ):
            is_aoe = True
            evidence.append("fragment explicitly describes multiple allies")
        elif any(
            phrase in lower
            for phrase in (
                "an ally",
                "target ally",
                "you are healed",
                "healing you",
                "you heal for",
                "heal for",
                "siphon ",
            )
        ):
            is_aoe = False
            evidence.append("fragment explicitly describes one recipient/self")

        if any(
            re.search(pattern, component_lower)
            for pattern in (
                r"\bevery\s+(?:\d+(?:\.\d+)?\s+)?seconds?\b",
                r"\bheal(?:ing|s)?\s+over\s+\d+(?:\.\d+)?\s+seconds?\b",
            )
        ):
            is_dot = True
            evidence.append("current coefficient explicitly describes periodic healing")
        else:
            is_dot = False
            evidence.append("current coefficient is an immediate/triggered heal without periodic wording")

    # Shields are their own effect family. ``is_dot`` and ``is_aoe`` are not
    # invented merely to make the row look complete. Recipient shape may be
    # added later when explicitly useful to a shield evaluator.

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
