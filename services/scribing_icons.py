from __future__ import annotations

"""Resolve configured scribed skills to the existing AbilityIcons asset names.

Grimoire stems mirror the U51 grimoire icon families. Focus suffixes mirror the
AbilityIcons scribed-skill filenames so the shared ESO icon resolver can find
local PNG assets without duplicating them into another catalog.
"""

GRIMOIRE_ICON_STEMS: dict[str, str] = {
    "Banner Bearer": "support",
    "Elemental Explosion": "staffdestro",
    "Mender's Bond": "staffresto",
    "Shield Throw": "1handed",
    "Smash": "2handed",
    "Soul Burst": "soulmagic2",
    "Torchbearer": "fightersguild",
    "Trample": "assault",
    "Traveling Knife": "dualwield",
    "Ulfsild's Contingency": "magesguild",
    "Vault": "bow",
    "Wield Soul": "soulmagic1",
}

FOCUS_ICON_SUFFIXES: dict[str, str] = {
    "Bleed Damage": "bleed",
    "Damage Shield": "shield",
    "Disease Damage": "disease",
    "Dispel": "dispel",
    "Flame Damage": "flame",
    "Frost Damage": "frost",
    "Generate Ultimate": "ultimate",
    "Healing": "heal",
    "Immobilize": "immobilize",
    "Knockback": "knockback",
    "Magic Damage": "magic",
    "Mitigation": "mitigation",
    "Multi-Target": "multitarget",
    "Physical Damage": "physical",
    "Poison Damage": "poison",
    "Pull": "pull",
    "Restore Resources": "resources",
    "Shock Damage": "shock",
    "Stun": "stun",
    "Taunt": "taunt",
    "Trauma": "trauma",
}

# AbilityIcons has no dedicated Traveling Knife + Pull texture. Use the
# existing base Traveling Knife icon rather than borrowing another Grimoire's
# pull art and presenting it as if it were canonical.
EXACT_TEXTURE_FALLBACKS: dict[tuple[str, str], str] = {
    ("Traveling Knife", "Pull"): "/esoui/art/icons/ability_grimoire_dualwield.dds",
}


def texture_for_scribed_skill(grimoire: str, focus: str) -> str:
    """Return an ESO-style texture path understood by the shared icon picker."""
    grimoire = str(grimoire or "").strip()
    focus = str(focus or "").strip()
    exact = EXACT_TEXTURE_FALLBACKS.get((grimoire, focus))
    if exact:
        return exact
    stem = GRIMOIRE_ICON_STEMS.get(grimoire)
    suffix = FOCUS_ICON_SUFFIXES.get(focus)
    if not stem or not suffix:
        return ""
    return f"/esoui/art/icons/ability_grimoire_{stem}_{suffix}.dds"
