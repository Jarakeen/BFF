from __future__ import annotations

"""Resolve configured scribed skills to the existing AbilityIcons asset names.

Only Grimoire family stems verified from the local AbilityIcons naming scheme
belong here. Focus suffixes mirror the icon pack's filenames.
"""

GRIMOIRE_ICON_STEMS: dict[str, str] = {
    "Wield Soul": "soulmagic1",
    "Soul Burst": "soulmagic2",
    "Elemental Explosion": "staffdestro",
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


def texture_for_scribed_skill(grimoire: str, focus: str) -> str:
    """Return an ESO-style texture path understood by the shared icon picker."""
    stem = GRIMOIRE_ICON_STEMS.get(str(grimoire or "").strip())
    suffix = FOCUS_ICON_SUFFIXES.get(str(focus or "").strip())
    if not stem or not suffix:
        return ""
    return f"/esoui/art/icons/ability_grimoire_{stem}_{suffix}.dds"
