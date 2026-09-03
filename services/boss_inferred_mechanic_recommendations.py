from __future__ import annotations

"""Conservative recommendations for reviewing inferred boss mechanics.

Recommendations are intentionally narrow. A mechanic is recommended for
acceptance only when every populated inferred field has direct textual support
in the source description. Unclear/unsupported fields keep the mechanic
pending. This module never writes review decisions or canonical facts.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable

from services.boss_inferred_mechanic_review import (
    InferredMechanicReviewRow,
    audit_inferred_boss_mechanics,
)

SUPPORTED = "supported"
UNCLEAR = "unclear"
UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class FieldSupport:
    field: str
    value: object
    status: str
    reason: str


@dataclass(frozen=True)
class MechanicRecommendation:
    row: InferredMechanicReviewRow
    field_support: tuple[FieldSupport, ...]
    recommended_status: str
    rationale: str


def _contains(text: str, patterns: Iterable[str]) -> bool:
    value = text.casefold()
    return any(re.search(pattern, value) for pattern in patterns)


def _support_mechanic_type(row: InferredMechanicReviewRow) -> FieldSupport:
    text = row.description.casefold()
    patterns = {
        "interrupt": (r"interrupt", r"can be interrupted", r"must be interrupted"),
        "charge": (r"\bcharge(?:s|d|ing)?\b", r"rush(?:es|ed|ing)? forward"),
        "summon": (r"\bsummon(?:s|ed|ing)?\b", r"\bspawns?\b", r"calls? .* aid"),
        "spread": (r"spread out", r"move away from", r"separate from"),
        "cleanse": (r"cleanse", r"purif", r"remove the effect"),
        "movement": (r"move", r"dodge", r"avoid", r"step out", r"run"),
        "positioning": (r"position", r"stand in", r"stand on", r"farthest", r"closest", r"behind", r"in front"),
        "hazard": (r"hazard", r"lingering", r"damage over time", r"remains? on the ground"),
        "targeted_hazard": (r"target", r"selected", r"chosen", r"poisoned targets?"),
        "area_attack": (r"aoe", r"area", r"circle", r"cone", r"around", r"all .* within", r"ground"),
    }
    pats = patterns.get(row.mechanic_type, ())
    if pats and _contains(text, pats):
        return FieldSupport("mechanic_type", row.mechanic_type, SUPPORTED, "description explicitly supports the inferred mechanic type")
    return FieldSupport("mechanic_type", row.mechanic_type, UNCLEAR, "mechanic type is not directly stated strongly enough for automatic acceptance")


def _support_damage_type(row: InferredMechanicReviewRow) -> FieldSupport | None:
    if not row.damage_type:
        return None
    aliases = {
        "physical": (r"physical",),
        "flame": (r"flame", r"fire damage"),
        "frost": (r"frost", r"ice damage"),
        "shock": (r"shock", r"lightning damage"),
        "magic": (r"magic damage", r"magical damage"),
        "poison": (r"poison",),
        "bleed": (r"bleed", r"bleeding"),
    }
    pats = aliases.get(row.damage_type.casefold(), ())
    if pats and _contains(row.description, pats):
        return FieldSupport("damage_type", row.damage_type, SUPPORTED, "damage type is explicit in the source description")
    return FieldSupport("damage_type", row.damage_type, UNCLEAR, "damage type is inferred but not explicit in the source description")


def _support_target_count(row: InferredMechanicReviewRow) -> FieldSupport | None:
    if row.target_count is None:
        return None
    text = row.description.casefold()
    words = {1: ("one", "a single"), 2: ("two", "2"), 3: ("three", "3"), 4: ("four", "4")}
    tokens = words.get(row.target_count, (str(row.target_count),))
    if any(token in text for token in tokens) and "target" in text:
        return FieldSupport("target_count", row.target_count, SUPPORTED, "target count is explicit in the source description")
    return FieldSupport("target_count", row.target_count, UNCLEAR, "target count is not explicit enough for automatic acceptance")


def _support_bool(field: str, value: bool | None, description: str) -> FieldSupport | None:
    if value is None:
        return None
    if value is False:
        return FieldSupport(field, value, UNCLEAR, "negative inferred booleans require manual review")
    patterns = {
        "requires_movement": (r"move", r"dodge", r"avoid", r"run", r"step out", r"walk into"),
        "requires_positioning": (r"position", r"stand in", r"stand on", r"farthest", r"closest", r"behind", r"in front", r"corner"),
        "requires_cleanse": (r"cleanse", r"remove the effect", r"purif"),
        "persistent_hazard": (r"lingering", r"damage over time", r"remains?", r"persistent", r"pool", r"rune"),
        "failure_is_fatal": (r"lethal", r"instant(?:ly)? kill", r"fatal", r"will kill"),
        "interruptible": (r"interrupt", r"can be interrupted", r"must be interrupted"),
    }
    if _contains(description, patterns.get(field, ())):
        return FieldSupport(field, value, SUPPORTED, "source description explicitly supports this boolean")
    return FieldSupport(field, value, UNCLEAR, "boolean is inferred but not explicit enough for automatic acceptance")


def recommend_mechanic(row: InferredMechanicReviewRow) -> MechanicRecommendation:
    checks: list[FieldSupport] = [_support_mechanic_type(row)]
    for item in (_support_damage_type(row), _support_target_count(row)):
        if item is not None:
            checks.append(item)
    for field in (
        "requires_movement",
        "requires_positioning",
        "requires_cleanse",
        "persistent_hazard",
        "failure_is_fatal",
        "interruptible",
    ):
        item = _support_bool(field, getattr(row, field), row.description)
        if item is not None:
            checks.append(item)

    accepted = checks and all(item.status == SUPPORTED for item in checks)
    if accepted:
        rationale = "All populated inferred fields are directly supported by the source description."
        status = "accepted"
    else:
        unclear = [item.field for item in checks if item.status != SUPPORTED]
        rationale = "Manual review retained for: " + ", ".join(unclear)
        status = "pending"
    return MechanicRecommendation(row, tuple(checks), status, rationale)


def load_content_ids_by_type(content_root: Path, content_type: str) -> set[str]:
    folder = {
        "trial": "trials",
        "dungeon": "dungeons",
        "arena": "arenas",
    }.get(content_type.casefold())
    if folder is None:
        raise ValueError(f"unsupported content type: {content_type!r}")
    ids: set[str] = set()
    for path in sorted((Path(content_root) / folder).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            value = str(payload.get("id") or "").strip()
            if value:
                ids.add(value)
    return ids


def build_recommendations(source_dir: Path, content_root: Path, *, content_type: str = "trial") -> tuple[MechanicRecommendation, ...]:
    audit = audit_inferred_boss_mechanics(source_dir)
    content_ids = load_content_ids_by_type(content_root, content_type)
    rows = [row for row in audit.rows if row.content_id in content_ids]
    return tuple(recommend_mechanic(row) for row in rows)
