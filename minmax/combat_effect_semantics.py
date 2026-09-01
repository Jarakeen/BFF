from __future__ import annotations

"""Game-update-aware canonical transitions for shared ESO combat effects.

This module deliberately separates two questions that must not be conflated:

1. What did a historical/source record actually say?
2. How should a legacy saved-build label migrate under the active game update?

Strict source resolution therefore fails closed when an effect has been removed.
Legacy-alias resolution may opt into a documented transition for compatibility.
"""

from dataclasses import dataclass
from enum import Enum


class GameUpdate(str, Enum):
    U50 = "U50"
    U51 = "U51"


@dataclass(frozen=True)
class EffectTransition:
    old_name: str
    new_name: str
    introduced_update: GameUpdate
    domain: str
    note: str


U51_TRANSITIONS: tuple[EffectTransition, ...] = (
    EffectTransition(
        "Minor Sorcery",
        "Minor Brutality",
        GameUpdate.U51,
        "buff",
        "Sorcery removed; Brutality provides both Weapon and Spell Damage.",
    ),
    EffectTransition(
        "Major Sorcery",
        "Major Brutality",
        GameUpdate.U51,
        "buff",
        "Sorcery removed; Brutality provides both Weapon and Spell Damage.",
    ),
    EffectTransition(
        "Minor Prophecy",
        "Minor Savagery",
        GameUpdate.U51,
        "buff",
        "Prophecy removed; Savagery provides both Weapon and Spell Critical Chance.",
    ),
    EffectTransition(
        "Major Prophecy",
        "Major Savagery",
        GameUpdate.U51,
        "buff",
        "Prophecy removed; Savagery provides both Weapon and Spell Critical Chance.",
    ),
    EffectTransition(
        "Increase Spell Power",
        "Increase Power",
        GameUpdate.U51,
        "alchemy",
        "Weapon and Spell Power traits consolidate into Increase Power.",
    ),
    EffectTransition(
        "Increase Weapon Power",
        "Increase Power",
        GameUpdate.U51,
        "alchemy",
        "Weapon and Spell Power traits consolidate into Increase Power.",
    ),
    EffectTransition(
        "Spell Critical",
        "Critical",
        GameUpdate.U51,
        "alchemy",
        "Weapon and Spell Critical traits consolidate into Critical.",
    ),
    EffectTransition(
        "Weapon Critical",
        "Critical",
        GameUpdate.U51,
        "alchemy",
        "Weapon and Spell Critical traits consolidate into Critical.",
    ),
    EffectTransition(
        "Maim",
        "Cowardice",
        GameUpdate.U51,
        "alchemy",
        "Alchemy Maim is removed and previously crafted potions migrate to Cowardice.",
    ),
)


# Source-visible U50 Alchemy effect names represented by recovered UESP pages or
# explicit formula evidence. Timidity, Ravage Magicka, and Ravage Stamina were
# omitted from the historical V3 expected set even though they are valid U50
# craftable Alchemy effects.
U50_ALCHEMY_TRAITS = frozenset(
    {
        "Breach",
        "Cowardice",
        "Defile",
        "Detection",
        "Enervation",
        "Entrapment",
        "Fracture",
        "Heroism",
        "Hindrance",
        "Increase Armor",
        "Increase Spell Power",
        "Increase Spell Resist",
        "Increase Weapon Power",
        "Invisible",
        "Lingering Health",
        "Maim",
        "Protection",
        "Ravage Health",
        "Ravage Magicka",
        "Ravage Stamina",
        "Restore Health",
        "Restore Magicka",
        "Restore Stamina",
        "Speed",
        "Spell Critical",
        "Timidity",
        "Uncertainty",
        "Unstoppable",
        "Vitality",
        "Weapon Critical",
    }
)


U51_NEW_ALCHEMY_TRAITS = frozenset(
    {
        "Mending",
        "Vexation",
        "Damage Shield",
        "Heal Absorption",
        "Force",
    }
)


U51_ALCHEMY_TRAITS = frozenset(
    {
        *(
            transition.new_name
            for transition in U51_TRANSITIONS
            if transition.domain == "alchemy"
        ),
        *(
            trait
            for trait in U50_ALCHEMY_TRAITS
            if trait
            not in {
                transition.old_name
                for transition in U51_TRANSITIONS
                if transition.domain == "alchemy"
            }
        ),
        *U51_NEW_ALCHEMY_TRAITS,
    }
)


def normalize_game_update(value: GameUpdate | str) -> GameUpdate:
    if isinstance(value, GameUpdate):
        return value
    text = str(value or "").strip().upper().replace("UPDATE ", "U")
    try:
        return GameUpdate(text)
    except ValueError as exc:
        raise ValueError(f"Unsupported ESO game update: {value!r}") from exc


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _transition_for(name: str, *, domain: str) -> EffectTransition | None:
    key = _norm(name)
    domain_key = _norm(domain)
    for transition in U51_TRANSITIONS:
        if _norm(transition.old_name) == key and _norm(transition.domain) == domain_key:
            return transition
    return None


def resolve_effect_name(
    name: str,
    *,
    domain: str,
    game_update: GameUpdate | str,
    allow_legacy_alias: bool = False,
) -> str | None:
    """Resolve one named effect under a specific ESO game update.

    U50 preserves the historical name. Under U51, removed/replaced names fail
    closed for strict source evidence. Callers adapting an old saved-build label
    may set ``allow_legacy_alias=True`` to migrate through the documented
    transition.
    """

    clean_name = " ".join(str(name or "").strip().split())
    if not clean_name:
        return None

    update = normalize_game_update(game_update)
    if update is GameUpdate.U50:
        return clean_name

    transition = _transition_for(clean_name, domain=domain)
    if transition is None:
        return clean_name
    if allow_legacy_alias:
        return transition.new_name
    return None


def resolve_buff_name(
    name: str,
    *,
    game_update: GameUpdate | str,
    allow_legacy_alias: bool = False,
) -> str | None:
    return resolve_effect_name(
        name,
        domain="buff",
        game_update=game_update,
        allow_legacy_alias=allow_legacy_alias,
    )


def resolve_alchemy_trait_name(
    name: str,
    *,
    game_update: GameUpdate | str,
    allow_legacy_alias: bool = False,
) -> str | None:
    return resolve_effect_name(
        name,
        domain="alchemy",
        game_update=game_update,
        allow_legacy_alias=allow_legacy_alias,
    )


def is_known_alchemy_trait(name: str, *, game_update: GameUpdate | str) -> bool:
    """Return whether a normalized trait belongs to the update's known vocabulary."""

    update = normalize_game_update(game_update)
    vocabulary = U50_ALCHEMY_TRAITS if update is GameUpdate.U50 else U51_ALCHEMY_TRAITS
    key = _norm(name)
    return any(_norm(trait) == key for trait in vocabulary)
