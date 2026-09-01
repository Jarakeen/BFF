from __future__ import annotations

"""Versioned Alchemy potion-trait -> named-combat-buff semantics.

The Alchemy trait name and the named combat buff it grants are related but not
identical identities. Keep that translation explicit so potion source evidence
can remain historical while combat-state semantics evolve by game update.
"""

from .combat_effect_semantics import GameUpdate, normalize_game_update


U50_POTION_TRAIT_BUFFS: dict[str, str] = {
    "Restore Health": "Major Fortitude",
    "Restore Magicka": "Major Intellect",
    "Restore Stamina": "Major Endurance",
    "Increase Spell Power": "Major Sorcery",
    "Increase Weapon Power": "Major Brutality",
    "Spell Critical": "Major Prophecy",
    "Weapon Critical": "Major Savagery",
}

# Update 51 consolidates Alchemy Power/Critical traits and removes the Sorcery /
# Prophecy named effects. Restore-resource potion semantics are unchanged here.
U51_POTION_TRAIT_BUFFS: dict[str, str] = {
    "Restore Health": "Major Fortitude",
    "Restore Magicka": "Major Intellect",
    "Restore Stamina": "Major Endurance",
    "Increase Power": "Major Brutality",
    "Critical": "Major Savagery",
}


def potion_buff_for_trait(
    trait: str,
    *,
    game_update: GameUpdate | str = GameUpdate.U50,
) -> str | None:
    update = normalize_game_update(game_update)
    key = " ".join(str(trait or "").strip().casefold().split())
    if not key:
        return None
    table = U50_POTION_TRAIT_BUFFS if update is GameUpdate.U50 else U51_POTION_TRAIT_BUFFS
    for source_trait, named_buff in table.items():
        if source_trait.casefold() == key:
            return named_buff
    return None
