from __future__ import annotations

from typing import Iterable

NON_COMBAT_SKILL_LINES = frozenset({"crafting", "racial", "thieves guild", "dark brotherhood", "excavation", "legerdemain", "scrying"})
SHARED_COMBAT_SKILL_LINES = frozenset({"two handed", "one hand and shield", "dual wield", "bow", "destruction staff", "restoration staff", "heavy armor", "medium armor", "light armor", "fighters guild", "mages guild", "psijic order", "soul magic", "undaunted", "assault", "support"})
VAMPIRE_SKILL_LINE = "vampire"
WEREWOLF_SKILL_LINE = "werewolf"
CLASS_SKILL_LINES = {
    "dragonknight": frozenset({"ardent flame", "draconic power", "earthen heart"}),
    "sorcerer": frozenset({"dark magic", "daedric summoning", "storm calling"}),
    "nightblade": frozenset({"assassination", "shadow", "siphoning"}),
    "templar": frozenset({"aedric spear", "dawn's wrath", "restoring light"}),
    "warden": frozenset({"animal companions", "green balance", "winter's embrace"}),
    "necromancer": frozenset({"grave lord", "bone tyrant", "living death"}),
    "arcanist": frozenset({"herald of the tome", "soldier of apocrypha", "curative runeforms"}),
}


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def is_ultimate(skill: dict) -> bool:
    return _int(skill.get("base_mechanic")) == 8


def is_player_active(skill: dict) -> bool:
    """Return whether a skill can participate in active-bar eligibility.

    Raw crafted rows remain excluded because they do not identify one actual
    configured scribed ability. The Build editor may explicitly mark a raw
    crafted row as selected for this saved build; that marker affects only UI
    eligibility and does not promote missing recipe semantics into capability
    truth. A synthetic/configured scribed entry is allowed when it carries the
    complete recipe payload injected for this build.
    """
    if _int(skill.get("is_player")) != 1 or _int(skill.get("is_passive")) != 0 or not _text(skill.get("name")):
        return False
    if _int(skill.get("is_crafted")) == 0:
        return True
    if bool(skill.get("editor_selectable_scribed")):
        return True
    recipe = skill.get("scribing_recipe")
    return isinstance(recipe, dict) and all(
        _text(recipe.get(field))
        for field in ("ResultName", "Grimoire", "Focus", "Signature", "Affix")
    )


def _class_allowed(skill: dict, character_class: str | None) -> bool:
    owner = _text(skill.get("class_type"))
    line = _text(skill.get("skill_line"))
    selected = _text(character_class)
    if owner:
        return bool(selected) and owner == selected and line in CLASS_SKILL_LINES.get(selected, frozenset())
    if line in NON_COMBAT_SKILL_LINES:
        return False
    return line in SHARED_COMBAT_SKILL_LINES or line in {VAMPIRE_SKILL_LINE, WEREWOLF_SKILL_LINE}


def is_eligible(skill: dict, *, character_class: str | None, slot_index: int, vampire: bool = False, werewolf: bool = False, transformed_form: str | None = None) -> bool:
    if vampire and werewolf or slot_index < 0 or slot_index > 5 or not is_player_active(skill):
        return False
    ultimate = is_ultimate(skill)
    if slot_index == 5 and not ultimate or slot_index < 5 and ultimate:
        return False
    line = _text(skill.get("skill_line"))
    if line in NON_COMBAT_SKILL_LINES or not _class_allowed(skill, character_class):
        return False
    if line == VAMPIRE_SKILL_LINE:
        return bool(vampire and _text(transformed_form) == VAMPIRE_SKILL_LINE)
    if line == WEREWOLF_SKILL_LINE:
        return bool(werewolf and _text(transformed_form) == WEREWOLF_SKILL_LINE)
    return True


def filter_skill_choices(skills: Iterable[dict], *, character_class: str | None, slot_index: int, vampire: bool = False, werewolf: bool = False, transformed_form: str | None = None) -> list[dict]:
    """Filter one bar slot; preserve morph identity, collapse rank duplicates."""
    selected: dict[tuple[int, int], dict] = {}
    for skill in skills:
        if not isinstance(skill, dict) or not is_eligible(skill, character_class=character_class, slot_index=slot_index, vampire=vampire, werewolf=werewolf, transformed_form=transformed_form):
            continue
        base_id = _int(skill.get("base_ability_id") or skill.get("ability_id") or skill.get("id"))
        morph = _int(skill.get("morph"))
        key = (base_id, morph)
        existing = selected.get(key)
        if existing is None or _int(skill.get("rank"), 999) < _int(existing.get("rank"), 999):
            selected[key] = skill
    return sorted(selected.values(), key=lambda s: (_text(s.get("name")), _int(s.get("base_ability_id") or s.get("ability_id") or s.get("id")), _int(s.get("morph"))))


def validate_bar(skills: Iterable[dict | None], *, character_class: str | None, vampire: bool = False, werewolf: bool = False, transformed_form: str | None = None) -> list[str]:
    values = list(skills)[:6]
    values += [None] * (6 - len(values))
    if vampire and werewolf:
        return ["A character cannot be both Vampire and Werewolf."]
    errors: list[str] = []
    for index, skill in enumerate(values):
        if skill is None:
            continue
        if not is_eligible(skill, character_class=character_class, slot_index=index, vampire=vampire, werewolf=werewolf, transformed_form=transformed_form):
            name = str(skill.get("name", "Unknown skill"))
            slot = "Ultimate" if index == 5 else f"Skill {index + 1}"
            errors.append(f"{slot}: {name} is not eligible for this bar slot.")
    return errors