from __future__ import annotations

from typing import Iterable

# These skill lines are intentionally excluded from every combat skill-bar
# picker. They may contain useful character/passive data elsewhere, but they
# are not equipable combat-bar content.
NON_COMBAT_SKILL_LINES = frozenset(
    {
        "crafting",
        "racial",
        "thieves guild",
        "dark brotherhood",
        "excavation",
        "legerdemain",
        "scrying",
    }
)

# Shared combat lines. Class lines are handled separately because the class
# must own the line before it can be equipped.
SHARED_COMBAT_SKILL_LINES = frozenset(
    {
        "two handed",
        "one hand and shield",
        "dual wield",
        "bow",
        "destruction staff",
        "restoration staff",
        "heavy armor",
        "medium armor",
        "light armor",
        "fighters guild",
        "mages guild",
        "psijic order",
        "soul magic",
        "undaunted",
        "assault",
        "support",
    }
)

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


def is_ultimate(skill: dict) -> bool:
    """Database ultimate marker used by the imported ability data."""
    try:
        return int(skill.get("base_mechanic", 0) or 0) == 8
    except (TypeError, ValueError):
        return False


def is_player_active(skill: dict) -> bool:
    """True only for player-controlled, non-passive, non-crafted abilities."""
    try:
        if int(skill.get("is_player", 0) or 0) != 1:
            return False
        if int(skill.get("is_passive", 0) or 0) != 0:
            return False
        if int(skill.get("is_crafted", 0) or 0) != 0:
            return False
    except (TypeError, ValueError):
        return False
    return bool(_text(skill.get("name")))


def _class_allowed(skill: dict, character_class: str | None) -> bool:
    owner = _text(skill.get("class_type"))
    line = _text(skill.get("skill_line"))
    selected = _text(character_class)

    if owner:
        return bool(selected) and owner == selected and line in CLASS_SKILL_LINES.get(selected, frozenset())

    if line in NON_COMBAT_SKILL_LINES:
        return False

    return line in SHARED_COMBAT_SKILL_LINES or line in {VAMPIRE_SKILL_LINE, WEREWOLF_SKILL_LINE}


def is_eligible(
    skill: dict,
    *,
    character_class: str | None,
    slot_index: int,
    vampire: bool = False,
    werewolf: bool = False,
    transformed_form: str | None = None,
) -> bool:
    """Determine whether an ability can occupy a particular combat-bar slot.

    Slots 0-4 are active combat abilities. Slot 5 is the sole ultimate slot.
    Vampire/Werewolf active abilities require the corresponding transformed
    form. Their passive benefits are deliberately outside this picker.
    """
    if vampire and werewolf:
        return False
    if slot_index < 0 or slot_index > 5:
        return False
    if not is_player_active(skill):
        return False

    ultimate = is_ultimate(skill)
    if slot_index == 5 and not ultimate:
        return False
    if slot_index < 5 and ultimate:
        return False

    line = _text(skill.get("skill_line"))
    if line in NON_COMBAT_SKILL_LINES:
        return False

    if not _class_allowed(skill, character_class):
        return False

    if line == VAMPIRE_SKILL_LINE:
        return bool(vampire and _text(transformed_form) == VAMPIRE_SKILL_LINE)
    if line == WEREWOLF_SKILL_LINE:
        return bool(werewolf and _text(transformed_form) == WEREWOLF_SKILL_LINE)

    return True


def filter_skill_choices(
    skills: Iterable[dict],
    *,
    character_class: str | None,
    slot_index: int,
    vampire: bool = False,
    werewolf: bool = False,
    transformed_form: str | None = None,
) -> list[dict]:
    """Return stable, deduplicated choices for one slot.

    Rank variants of the same ability are collapsed, but morphs are kept
    separate by `(base_ability_id, morph)` so both morph choices remain
    visible.
    """
    selected: dict[tuple[int, int, int], dict] = {}
    for skill in skills:
        if not isinstance(skill, dict) or not is_eligible(
            skill,
            character_class=character_class,
            slot_index=slot_index,
            vampire=vampire,
            werewolf=werewolf,
            transformed_form=transformed_form,
        ):
            continue
        try:
            base_id = int(skill.get("base_ability_id") or skill.get("ability_id") or skill.get("id") or 0)
        except (TypeError, ValueError):
            base_id = 0
        try:
            morph = int(skill.get("morph") or 0)
        except (TypeError, ValueError):
            morph = 0
        try:
            rank = int(skill.get("rank") or 0)
        except (TypeError, ValueError):
            rank = 0
        key = (base_id, morph, rank)
        existing = selected.get(key)
        if existing is None:
            selected[key] = skill

    return sorted(
        selected.values(),
        key=lambda s: (
            _text(s.get("name")),
            int(s.get("base_ability_id") or s.get("ability_id") or s.get("id") or 0),
            int(s.get("morph") or 0),
            int(s.get("rank") or 0),
        ),
    )


def validate_bar(
    skills: Iterable[dict | None],
    *,
    character_class: str | None,
    vampire: bool = False,
    werewolf: bool = False,
    transformed_form: str | None = None,
) -> list[str]:
    """Validate a six-slot bar against the same rules used by the picker."""
    values = list(skills)[:6]
    values += [None] * (6 - len(values))
    errors: list[str] = []
    if vampire and werewolf:
        errors.append("A character cannot be both Vampire and Werewolf.")
        return errors
    for index, skill in enumerate(values):
        if skill is None:
            continue
        if not is_eligible(
            skill,
            character_class=character_class,
            slot_index=index,
            vampire=vampire,
            werewolf=werewolf,
            transformed_form=transformed_form,
        ):
            name = str(skill.get("name", "Unknown skill"))
            slot = "Ultimate" if index == 5 else f"Skill {index + 1}"
            errors.append(f"{slot}: {name} is not eligible for this bar slot.")
    return errors
