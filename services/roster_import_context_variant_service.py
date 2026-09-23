from __future__ import annotations

"""Consolidate raid-roster loadouts into one base build plus sparse context variants.

Raid workbooks commonly keep one complete setup for trash/general play and several
alternate columns for bosses, portals, or other encounter jobs.  The importer should
not turn every column into an unrelated saved build.  This service keeps one complete
base payload and folds safely representable alternates into BuildContextVariant rows.

Named bosses win over ordinal labels.  Ordinals are resolved only when one trial can
be inferred from the other loadout labels.  Ambiguous or lossy cases stay as separate
builds rather than being guessed away.
"""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

from models.build_model import ARMOR_SLOTS, BuildContextVariant, GearSlot, PlayerBuild


_BASE_TOKENS = ("trash", "adds", "ads", "general", "default", "everywhere")
_WILDCARD_BOSS_LABELS = {"boss", "bosses", "all bosses", "boss setup", "boss setup(s)"}
_CONTEXT_ALIASES = {
    # Common raid shorthand that cannot be derived from the canonical display name.
    "twins": "lylanar_turlassil",
}
_GEAR_FIELDS = (
    "Set", "Set2", "Trait", "Enchant", "Weight", "Quality", "EnchantTier", "EnchantQuality", "Level", "WeaponType"
)


@dataclass(frozen=True)
class EncounterIdentity:
    content_id: str
    content_name: str
    encounter_id: str
    display_name: str
    member_ids: tuple[str, ...]
    order: int


@dataclass(frozen=True)
class ConsolidationReport:
    original_build_names: tuple[str, ...]
    imported_build_names: tuple[str, ...]
    folded_contexts: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return self.original_build_names != self.imported_build_names or bool(self.folded_contexts)


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).casefold())


def _load_identities(data_root: Path) -> tuple[EncounterIdentity, ...]:
    path = Path(data_root) / "raid_encounter_identity.json"
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    rows = payload.get("encounters") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return ()
    per_content_order: dict[str, int] = {}
    result: list[EncounterIdentity] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        content_id = _text(row.get("content_id"))
        content_name = _text(row.get("content_name"))
        encounter_id = _text(row.get("encounter_id"))
        display_name = _text(row.get("display_name"))
        member_ids = tuple(_text(item) for item in (row.get("member_ids") or []) if _text(item))
        if not content_id or not encounter_id or not display_name:
            continue
        order = per_content_order.get(content_id, 0) + 1
        per_content_order[content_id] = order
        result.append(
            EncounterIdentity(
                content_id=content_id,
                content_name=content_name,
                encounter_id=encounter_id,
                display_name=display_name,
                member_ids=member_ids,
                order=order,
            )
        )
    return tuple(result)


def _named_identity(label: str, identities: tuple[EncounterIdentity, ...]) -> EncounterIdentity | None:
    raw = _text(label)
    key = _key(raw)
    if not key:
        return None
    alias_id = _CONTEXT_ALIASES.get(key)
    if alias_id:
        return next((row for row in identities if row.encounter_id == alias_id), None)

    exact = [
        row
        for row in identities
        if key in {
            _key(row.encounter_id),
            _key(row.display_name),
            *(_key(member_id) for member_id in row.member_ids),
        }
    ]
    if len(exact) == 1:
        return exact[0]

    # Human sheets often shorten a unique boss name ("Reef", "Taleria").  Only
    # accept a substring when it resolves to exactly one reviewed encounter.
    if len(key) >= 4:
        partial = [row for row in identities if key in _key(row.display_name)]
        if len(partial) == 1:
            return partial[0]
    return None


def _context_pieces(build_name: str) -> list[str]:
    text = _text(build_name)
    if not text:
        return []
    folded = text.casefold()
    # "Bosses - Reef, Taleria" enumerates contexts.  Bare "Bosses" is handled as
    # the wildcard boss setup separately.
    if re.match(r"^\s*boss(?:es)?\s*[-:]", folded):
        text = re.split(r"[-:]", text, maxsplit=1)[1].strip()
    return [piece.strip() for piece in re.split(r"\s*,\s*|\s*/\s*", text) if piece.strip()]


def _is_base_candidate(name: str) -> bool:
    folded = _text(name).casefold()
    return any(re.search(rf"\b{re.escape(token)}\b", folded) for token in _BASE_TOKENS)


def _infer_content(candidates: Iterable[Any], identities: tuple[EncounterIdentity, ...]) -> str:
    content_ids: set[str] = set()
    for candidate in candidates:
        for piece in _context_pieces(getattr(candidate, "build_name", "")):
            identity = _named_identity(piece, identities)
            if identity is not None:
                content_ids.add(identity.content_id)
    return next(iter(content_ids)) if len(content_ids) == 1 else ""


def _ordinal_from_label(label: str) -> int | None:
    raw = _text(label).casefold()
    patterns = (
        r"\bboss\s*#?\s*(\d+)\b",
        r"\bb\s*#?\s*(\d+)\b",
        r"^\s*#?\s*(\d+)\s*(?:[-:]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return int(match.group(1))
    return None


def _resolve_context_label(
    label: str,
    *,
    identities: tuple[EncounterIdentity, ...],
    inferred_content_id: str,
) -> str:
    identity = _named_identity(label, identities)
    if identity is not None:
        return identity.display_name

    ordinal = _ordinal_from_label(label)
    if ordinal is not None and inferred_content_id:
        ordered = [row for row in identities if row.content_id == inferred_content_id]
        match = next((row for row in ordered if row.order == ordinal), None)
        if match is not None:
            return match.display_name

    # Keep explicit named jobs/add pulls as labels.  The encounter selector may
    # expose them from the broader encounter corpus even when they are not one of
    # the reviewed trial-boss identities.
    stripped = re.sub(r"\bboss\s*#?\s*\d+\b", "", _text(label), flags=re.IGNORECASE)
    stripped = re.sub(r"^\s*b\s*#?\s*\d+\b", "", stripped, flags=re.IGNORECASE)
    stripped = stripped.strip(" -:,")
    return stripped or _text(label)


def _gear_slot_diff(base: GearSlot, alt: GearSlot) -> tuple[GearSlot, bool]:
    values: dict[str, str] = {}
    lossy = False
    for field in _GEAR_FIELDS:
        before = _text(getattr(base, field, ""))
        after = _text(getattr(alt, field, ""))
        if before == after:
            continue
        if before and not after:
            lossy = True
            continue
        if after:
            values[field] = after
    return GearSlot(**values), lossy


def _bar_diff(base: list[str], alt: list[str]) -> tuple[list[str], bool]:
    result = [""] * 6
    lossy = False
    for index in range(6):
        before = _text(base[index] if index < len(base) else "")
        after = _text(alt[index] if index < len(alt) else "")
        if before == after:
            continue
        if before and not after:
            lossy = True
        elif after:
            result[index] = after
    return result, lossy


def sparse_variant(
    base_payload: dict[str, Any],
    alternate_payload: dict[str, Any],
    *,
    team_name: str,
    boss_name: str,
    source_label: str,
) -> tuple[BuildContextVariant | None, str]:
    """Return a lossless sparse variant or a reason it must remain a full build."""
    base = PlayerBuild.from_dict(base_payload)
    alt = PlayerBuild.from_dict(alternate_payload)

    unsupported_fields = (
        "Race", "EsoClass", "Role", "Vampire", "Werewolf",
        "AttributeHealth", "AttributeMagicka", "AttributeStamina",
        "ClassSkillLines", "ClassMasteryAbilityIds", "ScribedSkills", "ScribedSkillRecipes",
    )
    for field in unsupported_fields:
        if getattr(base, field) != getattr(alt, field):
            return None, f"{source_label}: {field} differs and is not a Context Variant field"

    lossy = False
    variant = BuildContextVariant(
        ContextType="Team + Boss",
        TeamName=_text(team_name),
        BossName=_text(boss_name),
        Notes=f"Imported context: {source_label}",
    )

    for field in ("Mundus", "SecondMundus", "Food", "Potion"):
        before = _text(getattr(base, field, ""))
        after = _text(getattr(alt, field, ""))
        if before == after:
            continue
        if before and not after:
            lossy = True
        elif after:
            setattr(variant, field, after)

    armor: dict[str, dict[str, str]] = {}
    for slot in ARMOR_SLOTS:
        before = base.Armor.get(slot, {})
        after = alt.Armor.get(slot, {})
        changed: dict[str, str] = {}
        for field in _GEAR_FIELDS:
            b = _text(before.get(field, ""))
            a = _text(after.get(field, ""))
            if b == a:
                continue
            if b and not a:
                lossy = True
            elif a:
                changed[field] = a
        if changed:
            armor[slot] = changed
    variant.Armor = armor

    for field in (
        "FrontBarWeapon", "FrontBarOffHand", "BackBarWeapon", "BackBarOffHand",
        "Necklace", "Ring1", "Ring2",
    ):
        diff, field_lossy = _gear_slot_diff(getattr(base, field), getattr(alt, field))
        setattr(variant, field, diff)
        lossy = lossy or field_lossy

    variant.FrontBarSkills, front_lossy = _bar_diff(base.FrontBarSkills, alt.FrontBarSkills)
    variant.BackBarSkills, back_lossy = _bar_diff(base.BackBarSkills, alt.BackBarSkills)
    lossy = lossy or front_lossy or back_lossy

    if base.ChampionPoints != alt.ChampionPoints:
        if base.ChampionPoints and not alt.ChampionPoints:
            lossy = True
        elif alt.ChampionPoints:
            variant.ChampionPoints = deepcopy(alt.ChampionPoints)

    if lossy:
        return None, f"{source_label}: alternate clears base values that sparse variants cannot safely clear"

    meaningful = bool(
        variant.Mundus
        or variant.SecondMundus
        or variant.Armor
        or not variant.FrontBarWeapon.is_empty
        or not variant.FrontBarOffHand.is_empty
        or not variant.BackBarWeapon.is_empty
        or not variant.BackBarOffHand.is_empty
        or not variant.Necklace.is_empty
        or not variant.Ring1.is_empty
        or not variant.Ring2.is_empty
        or variant.ChampionPoints
        or any(variant.FrontBarSkills)
        or any(variant.BackBarSkills)
        or variant.Food
        or variant.Potion
    )
    return (variant if meaningful else None), ""


def consolidate_member_builds(
    candidates: list[Any],
    *,
    team_name: str,
    data_root: Path,
) -> tuple[list[Any], ConsolidationReport]:
    """Fold safe alternates under one base candidate; keep ambiguous/lossy rows separate."""
    original = [deepcopy(candidate) for candidate in candidates]
    original_names = tuple(_text(getattr(candidate, "build_name", "")) for candidate in original)
    if len(original) <= 1:
        return original, ConsolidationReport(original_names, original_names, (), ())

    identities = _load_identities(Path(data_root))
    inferred_content_id = _infer_content(original, identities)

    base_index = next(
        (index for index, candidate in enumerate(original) if _is_base_candidate(getattr(candidate, "build_name", ""))),
        0,
    )
    base = deepcopy(original[base_index])
    base_payload = deepcopy(getattr(base, "payload", {}) or {})
    existing_variants = list(base_payload.get("ContextVariants") or [])
    folded_contexts: list[str] = []
    warnings: list[str] = []
    extras: list[Any] = []

    for index, candidate in enumerate(original):
        if index == base_index:
            continue
        name = _text(getattr(candidate, "build_name", ""))
        name_key = _text(name).casefold()
        if name_key in _WILDCARD_BOSS_LABELS:
            context_labels = ["*"]
        else:
            context_labels = _context_pieces(name)

        # A special-job label with no boss/ordinal/context relationship cannot be
        # selected safely by the current Team/Boss resolver. Keep it as a full build.
        resolved_labels: list[str] = []
        for label in context_labels:
            if label == "*":
                resolved_labels.append("*")
                continue
            resolved = _resolve_context_label(
                label,
                identities=identities,
                inferred_content_id=inferred_content_id,
            )
            if resolved:
                resolved_labels.append(resolved)

        if not resolved_labels:
            extras.append(candidate)
            warnings.append(f"{name}: no safe boss/context label was found; kept as a separate build")
            continue

        variants_for_candidate: list[BuildContextVariant] = []
        failed_reason = ""
        for boss_name in resolved_labels:
            variant, reason = sparse_variant(
                base_payload,
                getattr(candidate, "payload", {}) or {},
                team_name=team_name,
                boss_name=boss_name,
                source_label=name,
            )
            if reason:
                failed_reason = reason
                break
            if variant is not None:
                variants_for_candidate.append(variant)

        if failed_reason:
            extras.append(candidate)
            warnings.append(failed_reason + "; kept as a separate build")
            continue

        for variant in variants_for_candidate:
            existing_variants.append(variant.to_dict())
            folded_contexts.append(variant.BossName)

    base_payload["ContextVariants"] = existing_variants
    base.payload = base_payload
    imported = [base, *extras]
    imported_names = tuple(_text(getattr(candidate, "build_name", "")) for candidate in imported)
    return imported, ConsolidationReport(
        original_build_names=original_names,
        imported_build_names=imported_names,
        folded_contexts=tuple(folded_contexts),
        warnings=tuple(warnings),
    )


__all__ = [
    "ConsolidationReport",
    "consolidate_member_builds",
    "sparse_variant",
]
