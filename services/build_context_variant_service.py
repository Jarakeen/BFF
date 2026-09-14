from __future__ import annotations

"""Resolve sparse team/boss build variants over one canonical saved build.

Precedence is deliberately narrow and deterministic:
exact team + boss > wildcard team + any boss > team > exact boss > wildcard boss > base.

Resolution is field-by-field. Lower-specificity matching variants are applied first,
so a sparse exact Team + Boss row can inherit from a generic Bosses setup instead of
falling all the way back to the base build.
"""

from copy import deepcopy

from models.build_model import ARMOR_SLOTS, BuildContextVariant, GearSlot, PlayerBuild


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _is_boss_wildcard(value: object) -> bool:
    return _key(value) in {"*", "any boss", "all bosses", "bosses"}


def _context_score(variant: BuildContextVariant, team_name: str, boss_name: str) -> int:
    kind = _key(variant.ContextType)
    team_matches = bool(_key(team_name)) and _key(variant.TeamName) == _key(team_name)
    has_boss_context = bool(_key(boss_name))
    boss_matches = has_boss_context and _key(variant.BossName) == _key(boss_name)
    boss_wildcard = has_boss_context and _is_boss_wildcard(variant.BossName)
    if kind in {"team + boss", "team+boss", "team boss"}:
        if team_matches and boss_matches:
            return 30
        if team_matches and boss_wildcard:
            return 25
        return -1
    if kind == "team":
        return 20 if team_matches else -1
    if kind == "boss":
        if boss_matches:
            return 10
        if boss_wildcard:
            return 5
        return -1
    return -1


def _matching_variants(
    build: PlayerBuild,
    *,
    team_name: str = "",
    boss_name: str = "",
) -> tuple[tuple[int, BuildContextVariant], ...]:
    """Return at most one matching row per specificity, least to most specific."""
    latest_by_score: dict[int, tuple[int, BuildContextVariant]] = {}
    for index, variant in enumerate(build.ContextVariants):
        score = _context_score(variant, team_name, boss_name)
        if score < 0:
            continue
        latest_by_score[score] = (index, variant)
    return tuple(
        (score, latest_by_score[score][1])
        for score in sorted(latest_by_score)
    )


def select_context_variant(
    build: PlayerBuild,
    *,
    team_name: str = "",
    boss_name: str = "",
) -> BuildContextVariant | None:
    matches = _matching_variants(build, team_name=team_name, boss_name=boss_name)
    return matches[-1][1] if matches else None


def _overlay_bar(base: list[str], override: list[str]) -> list[str]:
    result = list(base)
    if len(result) < 6:
        result.extend([""] * (6 - len(result)))
    for index, value in enumerate(list(override or [])[:6]):
        text = str(value or "").strip()
        if text:
            result[index] = text
    return result[:6]


def _overlay_gear(base: GearSlot, override: GearSlot) -> GearSlot:
    if override.is_empty:
        return deepcopy(base)
    result = deepcopy(base)
    for field in (
        "Set",
        "Set2",
        "Trait",
        "Enchant",
        "Weight",
        "Quality",
        "EnchantTier",
        "Level",
        "WeaponType",
    ):
        value = str(getattr(override, field, "") or "").strip()
        if value:
            setattr(result, field, value)
    return result


def apply_context_variant(build: PlayerBuild, variant: BuildContextVariant) -> PlayerBuild:
    result = deepcopy(build)
    result.ContextVariants = deepcopy(build.ContextVariants)

    if str(variant.Mundus or "").strip():
        result.Mundus = variant.Mundus
    if str(variant.SecondMundus or "").strip():
        result.SecondMundus = variant.SecondMundus

    for slot in ARMOR_SLOTS:
        override = variant.Armor.get(slot)
        if not override:
            continue
        current = dict(result.Armor.get(slot) or {})
        for key, value in override.items():
            text = str(value or "").strip()
            if text:
                current[str(key)] = text
        result.Armor[slot] = current

    result.FrontBarWeapon = _overlay_gear(result.FrontBarWeapon, variant.FrontBarWeapon)
    result.FrontBarOffHand = _overlay_gear(result.FrontBarOffHand, variant.FrontBarOffHand)
    result.BackBarWeapon = _overlay_gear(result.BackBarWeapon, variant.BackBarWeapon)
    result.BackBarOffHand = _overlay_gear(result.BackBarOffHand, variant.BackBarOffHand)
    result.Necklace = _overlay_gear(result.Necklace, variant.Necklace)
    result.Ring1 = _overlay_gear(result.Ring1, variant.Ring1)
    result.Ring2 = _overlay_gear(result.Ring2, variant.Ring2)

    if variant.ChampionPoints:
        result.ChampionPoints = deepcopy(variant.ChampionPoints)
    result.FrontBarSkills = _overlay_bar(result.FrontBarSkills, variant.FrontBarSkills)
    result.BackBarSkills = _overlay_bar(result.BackBarSkills, variant.BackBarSkills)

    if str(variant.Food or "").strip():
        result.Food = variant.Food
    if str(variant.Potion or "").strip():
        result.Potion = variant.Potion
    return result


def resolve_build_context(
    build: PlayerBuild,
    *,
    team_name: str = "",
    boss_name: str = "",
) -> PlayerBuild:
    matches = _matching_variants(build, team_name=team_name, boss_name=boss_name)
    result = deepcopy(build)
    for _score, variant in matches:
        result = apply_context_variant(result, variant)
    return result


__all__ = [
    "apply_context_variant",
    "resolve_build_context",
    "select_context_variant",
]
