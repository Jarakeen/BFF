"""Parsers for structured values found in ESO tooltip descriptions."""

from __future__ import annotations

import re
from html import unescape
from typing import Final


_EFFECT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:Major|Minor)\s+"
    r"([A-Z][A-Za-z'\u2019\u2013-]*(?:\s+[A-Z][A-Za-z'\u2019\u2013-]*)*)"
)
_DURATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:for|lasts?|duration(?:\s+of)?)\s+"
    r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\b",
    re.IGNORECASE,
)
_DISTANCE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:range|radius)\s*(?:of|:)?\s*"
    r"(\d+(?:\.\d+)?)\s*(meters?|metres?|m)\b"
    r"|\bwithin\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*(meters?|metres?|m)\b",
    re.IGNORECASE,
)
_RADIUS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:\b(?:radius\s*(?:of|:)?\s*|within\s+(?:a\s+)?)"
    r"(\d+(?:\.\d+)?)\s*(meters?|metres?|m)\b"
    r"|\b(\d+(?:\.\d+)?)\s*(meters?|metres?|m)\s+radius\b)",
    re.IGNORECASE,
)
_COOLDOWN_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:ability\s+)?cooldown(?:\s+of|\s*[:=])?\s*"
    r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m)\b",
    re.IGNORECASE,
)
_COEFFICIENT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:coeff(?:icient)?\s*)?([ab])\s*[:=]\s*"
    r"([+-]?\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_SET_BONUS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[.;])\s*(?:5\s*(?:pieces?|items?)|five\s*(?:pieces?|items?))\s*[:\-]?\s*"
    r"(.+?)(?=(?:[.;]\s*(?:\d+|one|two|three|four|five)\s*(?:pieces?|items?)\b|$))",
    re.IGNORECASE,
)


def parse_effects(description: str) -> list[str]:
    """Return unique Major/Minor effect names in first-seen order."""
    if not description:
        return []

    effects: list[str] = []
    seen: set[str] = set()
    for match in _EFFECT_PATTERN.finditer(description):
        effect_name = match.group(1)
        if effect_name not in seen:
            seen.add(effect_name)
            effects.append(effect_name)
    return effects


def parse_duration(description: str) -> float | None:
    """Return the first tooltip duration normalized to seconds."""
    if not description:
        return None

    match = _DURATION_PATTERN.search(description)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"h", "hr", "hrs", "hour", "hours"}:
        return value * 3600
    if unit in {"m", "min", "mins", "minute", "minutes"}:
        return value * 60
    return value


def parse_range(description: str) -> float | None:
    """Return the first tooltip range normalized to meters."""
    if not description:
        return None

    match = _DISTANCE_PATTERN.search(description)
    if not match:
        return None

    value = match.group(1) or match.group(3)
    return float(value)


def parse_radius(description: str) -> float | None:
    """Return the first tooltip area radius normalized to meters."""
    if not description:
        return None

    match = _RADIUS_PATTERN.search(description)
    if not match:
        return None

    return float(match.group(1) or match.group(3))


def parse_description(description: str) -> str:
    """Return tooltip text with markup, entities, and excess whitespace removed."""
    if not description:
        return ""

    without_markup = re.sub(r"<[^>]+>", " ", description)
    normalized = " ".join(unescape(without_markup).split())
    return re.sub(r"\s+([,.;:!?])", r"\1", normalized)


def parse_target(description: str) -> str | None:
    """Return the normalized target scope described by a tooltip."""
    text = parse_description(description).lower()
    if not text:
        return None

    if re.search(r"\b(?:allies|group members|group)\b", text):
        return "group"
    if re.search(r"\b(?:enemy|enemies|foe|foes|target)\b", text):
        return "enemy"
    if re.search(r"\b(?:you|your|yourself|self)\b", text):
        return "self"
    return None


def parse_abilityCooldown(description: str) -> float | None:
    """Return an ability cooldown normalized to seconds."""
    match = _COOLDOWN_PATTERN.search(parse_description(description))
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2).lower()
    return value * 60 if unit in {"m", "min", "mins", "minute", "minutes"} else value


def parse_skillCoef(description: str) -> dict[str, float]:
    """Return explicitly labeled skill coefficients as ``coeff_a`` and ``coeff_b``."""
    coefficients: dict[str, float] = {}
    for match in _COEFFICIENT_PATTERN.finditer(parse_description(description)):
        coefficients[f"coeff_{match.group(1).lower()}"] = float(match.group(2))
    return coefficients


def parse_armortype(description: str) -> int | None:
    """Return ESO armor weight: light=1, medium=2, heavy=3."""
    text = parse_description(description).lower()
    for armor_name, armor_type in (("light", 1), ("medium", 2), ("heavy", 3)):
        if re.search(rf"\b{armor_name}\s+armor\b", text):
            return armor_type
    return None


def parse_setBonusDesc5(description: str) -> str | None:
    """Return the text of a set's five-piece bonus, when present."""
    match = _SET_BONUS_PATTERN.search(parse_description(description))
    return match.group(1).strip().rstrip(".;") if match else None


def parse_stat(description: str, stat_name: str) -> int | None:
    """Return the first integer value immediately preceding a named stat."""
    if not description or not stat_name:
        return None

    match = re.search(
        rf"\b(\d+)\s+{re.escape(stat_name)}\b",
        parse_description(description),
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


__all__ = [
    "parse_effects",
    "parse_duration",
    "parse_range",
    "parse_radius",
    "parse_description",
    "parse_target",
    "parse_abilityCooldown",
    "parse_skillCoef",
    "parse_armortype",
    "parse_setBonusDesc5",
    "parse_stat",
]
