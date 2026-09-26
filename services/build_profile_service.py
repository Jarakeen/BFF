from __future__ import annotations

"""Persistent Phase 14 build profile metadata.

The profile is additive user state layered over an existing saved build. Existing
explicit gear values remain authoritative overrides; no saved build or database row
is normalized or deleted merely because a default exists.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from services.build_profile_pydantic_schema import (
    validate_build_profile_payload,
    validate_build_profile_store_payload,
)

DEFAULT_QUALITY = "Gold"
DEFAULT_ITEM_LEVEL = "CP160"
DEFAULT_ENCHANTMENT_TIER = "Truly Superb"
DEFAULT_ARMOR_TRAIT = ""
DEFAULT_ARMOR_WEIGHT = ""
DEFAULT_ARMOR_ENCHANT = ""
DEFAULT_JEWELRY_TRAIT = ""
DEFAULT_JEWELRY_ENCHANT = ""


@dataclass(frozen=True)
class BuildProfile:
    quality: str = DEFAULT_QUALITY
    item_level: str = DEFAULT_ITEM_LEVEL
    enchantment_tier: str = DEFAULT_ENCHANTMENT_TIER
    armor_trait: str = DEFAULT_ARMOR_TRAIT
    armor_weight: str = DEFAULT_ARMOR_WEIGHT
    armor_enchant: str = DEFAULT_ARMOR_ENCHANT
    jewelry_trait: str = DEFAULT_JEWELRY_TRAIT
    jewelry_enchant: str = DEFAULT_JEWELRY_ENCHANT
    favorite: bool = False
    archived: bool = False
    ownership: str = "mine"
    source_owner: str = ""
    source_template_id: str = ""

    def normalized(self) -> "BuildProfile":
        ownership = str(self.ownership or "mine").strip().casefold()
        if ownership not in {"mine", "team"}:
            ownership = "mine"
        return BuildProfile(
            quality=str(self.quality or DEFAULT_QUALITY).strip() or DEFAULT_QUALITY,
            item_level=str(self.item_level or DEFAULT_ITEM_LEVEL).strip() or DEFAULT_ITEM_LEVEL,
            enchantment_tier=str(self.enchantment_tier or DEFAULT_ENCHANTMENT_TIER).strip() or DEFAULT_ENCHANTMENT_TIER,
            armor_trait=str(self.armor_trait or "").strip(),
            armor_weight=str(self.armor_weight or "").strip(),
            armor_enchant=str(self.armor_enchant or "").strip(),
            jewelry_trait=str(self.jewelry_trait or "").strip(),
            jewelry_enchant=str(self.jewelry_enchant or "").strip(),
            favorite=bool(self.favorite),
            archived=bool(self.archived),
            ownership=ownership,
            source_owner=str(self.source_owner or "").strip(),
            source_template_id=str(self.source_template_id or "").strip(),
        )


@dataclass(frozen=True)
class EffectiveItemProfile:
    quality: str
    item_level: str
    enchantment_tier: str
    quality_overridden: bool
    item_level_overridden: bool
    enchantment_tier_overridden: bool

    @property
    def has_override(self) -> bool:
        return any((self.quality_overridden, self.item_level_overridden, self.enchantment_tier_overridden))


class BuildProfileService:
    """Read/write additive profile records keyed by canonical saved-build id."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load_payload(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "profiles": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "profiles": {}}
        try:
            return validate_build_profile_store_payload(payload)
        except ValueError as exc:
            raise ValueError(f"Build profile store failed Pydantic validation: {exc}") from exc

    def get(self, build_id: str) -> BuildProfile:
        key = str(build_id or "").strip()
        if not key:
            return BuildProfile()
        row = self._load_payload()["profiles"].get(key)
        if not isinstance(row, dict):
            return BuildProfile()
        try:
            row = validate_build_profile_payload(row)
        except ValueError:
            return BuildProfile()
        return BuildProfile(
            quality=str(row.get("quality") or DEFAULT_QUALITY),
            item_level=str(row.get("item_level") or DEFAULT_ITEM_LEVEL),
            enchantment_tier=str(row.get("enchantment_tier") or DEFAULT_ENCHANTMENT_TIER),
            armor_trait=str(row.get("armor_trait") or ""),
            armor_weight=str(row.get("armor_weight") or ""),
            armor_enchant=str(row.get("armor_enchant") or ""),
            jewelry_trait=str(row.get("jewelry_trait") or ""),
            jewelry_enchant=str(row.get("jewelry_enchant") or ""),
            favorite=bool(row.get("favorite", False)),
            archived=bool(row.get("archived", False)),
            ownership=str(row.get("ownership") or "mine"),
            source_owner=str(row.get("source_owner") or ""),
            source_template_id=str(row.get("source_template_id") or ""),
        ).normalized()

    def put(self, build_id: str, profile: BuildProfile) -> None:
        key = str(build_id or "").strip()
        if not key:
            raise ValueError("build_id is required")
        payload = self._load_payload()
        profiles = dict(payload["profiles"])
        profiles[key] = validate_build_profile_payload(asdict(profile.normalized()))
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        persisted_payload = validate_build_profile_store_payload(
            {"version": 1, "profiles": profiles}
        )
        temporary.write_text(
            json.dumps(persisted_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        try:
            read_back = json.loads(self.path.read_text(encoding="utf-8"))
            read_back = validate_build_profile_store_payload(read_back)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Build profile save failed read-back validation: {exc}") from exc
        if read_back != persisted_payload:
            raise ValueError("Build profile save did not round-trip exactly")

    def update(self, build_id: str, **changes: Any) -> BuildProfile:
        current = asdict(self.get(build_id))
        for key, value in changes.items():
            if key not in current:
                raise ValueError(f"Unknown build profile field: {key}")
            current[key] = value
        updated = BuildProfile(**current).normalized()
        self.put(build_id, updated)
        return updated


def effective_item_profile(item, profile: BuildProfile) -> EffectiveItemProfile:
    if hasattr(item, "Quality"):
        quality = str(getattr(item, "Quality", "") or "").strip()
        item_level = str(getattr(item, "Level", "") or "").strip()
        enchantment_tier = str(getattr(item, "EnchantTier", "") or "").strip()
    elif isinstance(item, dict):
        quality = str(item.get("Quality") or "").strip()
        item_level = str(item.get("Level") or "").strip()
        enchantment_tier = str(item.get("EnchantTier") or "").strip()
    else:
        quality = item_level = enchantment_tier = ""
    normalized = profile.normalized()
    return EffectiveItemProfile(
        quality=quality or normalized.quality,
        item_level=item_level or normalized.item_level,
        enchantment_tier=enchantment_tier or normalized.enchantment_tier,
        quality_overridden=bool(quality and quality.casefold() != normalized.quality.casefold()),
        item_level_overridden=bool(item_level and item_level.casefold() != normalized.item_level.casefold()),
        enchantment_tier_overridden=bool(enchantment_tier and enchantment_tier.casefold() != normalized.enchantment_tier.casefold()),
    )


def build_profile_exception_count(build, profile: BuildProfile) -> int:
    items = list(getattr(build, "Armor", {}).values())
    items.extend([
        getattr(build, "Necklace", None), getattr(build, "Ring1", None), getattr(build, "Ring2", None),
        getattr(build, "FrontBarWeapon", None), getattr(build, "FrontBarOffHand", None),
        getattr(build, "BackBarWeapon", None), getattr(build, "BackBarOffHand", None),
    ])
    return sum(1 for item in items if item is not None and effective_item_profile(item, profile).has_override)


def build_with_effective_item_profile(build, profile: BuildProfile):
    """Return a calculation copy with the baseline on equipped, blank item fields.

    This does not write the Saved Build. Explicit item values retain authority,
    and an empty slot must not become equipped merely because a baseline exists.
    """
    resolved = deepcopy(build)

    def apply(item) -> None:
        effective = effective_item_profile(item, profile)
        if isinstance(item, dict):
            item.setdefault("Quality", "")
            item.setdefault("Level", "")
            item.setdefault("EnchantTier", "")
            item["Quality"] = str(item["Quality"] or "").strip() or effective.quality
            item["Level"] = str(item["Level"] or "").strip() or effective.item_level
            item["EnchantTier"] = str(item["EnchantTier"] or "").strip() or effective.enchantment_tier
        else:
            item.Quality = str(item.Quality or "").strip() or effective.quality
            item.Level = str(item.Level or "").strip() or effective.item_level
            item.EnchantTier = str(item.EnchantTier or "").strip() or effective.enchantment_tier

    normalized = profile.normalized()
    for item in resolved.Armor.values():
        if any(str(item.get(key) or "").strip() for key in ("Set", "Set2", "Weight", "Trait", "Enchant")):
            apply(item)
            item.setdefault("Trait", "")
            item.setdefault("Weight", "")
            item.setdefault("Enchant", "")
            item["Trait"] = str(item["Trait"] or "").strip() or normalized.armor_trait
            item["Weight"] = str(item["Weight"] or "").strip() or normalized.armor_weight
            item["Enchant"] = str(item["Enchant"] or "").strip() or normalized.armor_enchant
    for name in ("Necklace", "Ring1", "Ring2"):
        item = getattr(resolved, name)
        if not item.is_empty:
            apply(item)
            item.Trait = str(item.Trait or "").strip() or normalized.jewelry_trait
            item.Enchant = str(item.Enchant or "").strip() or normalized.jewelry_enchant
    for name in ("FrontBarWeapon", "FrontBarOffHand", "BackBarWeapon", "BackBarOffHand"):
        item = getattr(resolved, name)
        if not item.is_empty:
            apply(item)
    return resolved


__all__ = ["BuildProfile", "BuildProfileService", "EffectiveItemProfile", "DEFAULT_QUALITY", "DEFAULT_ITEM_LEVEL", "DEFAULT_ENCHANTMENT_TIER", "effective_item_profile", "build_profile_exception_count", "build_with_effective_item_profile"]
