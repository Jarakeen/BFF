from __future__ import annotations

"""Static ESO scribing catalogue.

Source: UESP Online:Scribing overview saved 2026-08-30.
The overview supplies Grimoire skill lines and each script's compatible
Grimoires. It does not enumerate every forbidden Focus/Signature/Affix
cross-combination, so this module deliberately validates Grimoire
compatibility only. Result names are explicit mappings, never inferred.
"""

GRIMOIRE_SKILL_LINES: dict[str, str] = {
    'Elemental Explosion': 'Destruction Staff',
    "Mender's Bond": 'Restoration Staff',
    'Shield Throw': 'One Hand and Shield',
    'Smash': 'Two Handed',
    'Traveling Knife': 'Dual Wield',
    'Vault': 'Bow',
    'Wield Soul': 'Soul Magic',
    'Soul Burst': 'Soul Magic',
    'Torchbearer': 'Fighters Guild',
    "Ulfsild's Contingency": 'Mages Guild',
    'Banner Bearer': 'Support',
    'Trample': 'Assault'
}

FOCUS_COMPATIBILITY: dict[str, tuple[str, ...]] = {
    'Bleed Damage': ('Smash', 'Traveling Knife', 'Vault', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency"),
    'Damage Shield': ("Mender's Bond", 'Smash', 'Wield Soul', 'Soul Burst', "Ulfsild's Contingency"),
    'Disease Damage': ('Vault', 'Wield Soul', 'Soul Burst', 'Trample'),
    'Dispel': ('Elemental Explosion', 'Trample'),
    'Flame Damage': ('Elemental Explosion', 'Vault', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency", 'Banner Bearer'),
    'Frost Damage': ('Elemental Explosion', 'Shield Throw', 'Traveling Knife', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency", 'Trample'),
    'Generate Ultimate': ("Mender's Bond", 'Torchbearer'),
    'Healing': ("Mender's Bond", 'Smash', 'Vault', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency"),
    'Immobilize': ("Mender's Bond", 'Shield Throw', 'Vault', 'Soul Burst', "Ulfsild's Contingency", 'Banner Bearer'),
    'Knockback': ('Elemental Explosion', 'Shield Throw', 'Smash', 'Torchbearer', "Ulfsild's Contingency", 'Trample'),
    'Magic Damage': ('Elemental Explosion', "Mender's Bond", 'Shield Throw', 'Smash', 'Traveling Knife', 'Wield Soul', 'Soul Burst', "Ulfsild's Contingency", 'Banner Bearer', 'Trample'),
    'Mitigation': ("Mender's Bond", 'Banner Bearer'),
    'Multi-Target': ('Shield Throw', 'Traveling Knife', 'Banner Bearer'),
    'Physical Damage': ('Elemental Explosion', 'Shield Throw', 'Smash', 'Traveling Knife', 'Wield Soul', 'Soul Burst', 'Torchbearer', 'Banner Bearer', 'Trample'),
    'Poison Damage': ('Smash', 'Traveling Knife', 'Vault'),
    'Pull': ('Shield Throw', 'Traveling Knife', 'Wield Soul', 'Soul Burst'),
    'Restore Resources': ("Mender's Bond", 'Banner Bearer'),
    'Shock Damage': ('Elemental Explosion', 'Wield Soul', 'Soul Burst', "Ulfsild's Contingency", 'Banner Bearer'),
    'Stun': ('Elemental Explosion', 'Smash', 'Traveling Knife', 'Wield Soul', 'Torchbearer', 'Trample'),
    'Taunt': ('Shield Throw', 'Smash', 'Vault'),
    'Trauma': ('Elemental Explosion', 'Trample')
}

SIGNATURE_COMPATIBILITY: dict[str, tuple[str, ...]] = {
    "Anchorite's Cruelty": ('Wield Soul', 'Soul Burst'),
    "Anchorite's Potency": ('Wield Soul', 'Soul Burst'),
    "Assassin's Misery": ('Elemental Explosion', 'Traveling Knife', 'Trample'),
    "Cavalier's Charge": ('Banner Bearer', 'Trample'),
    'Class Flourish': ('Elemental Explosion', "Mender's Bond", 'Shield Throw', 'Smash', 'Traveling Knife', 'Vault', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency", 'Banner Bearer', 'Trample'),
    "Crusader's Defiance": ("Mender's Bond", 'Smash', 'Vault', 'Soul Burst', 'Torchbearer', 'Banner Bearer'),
    "Druid's Resurgence": ('Elemental Explosion', "Mender's Bond", 'Shield Throw', 'Smash', 'Vault', 'Wield Soul', 'Torchbearer', 'Banner Bearer'),
    "Fencer's Parry": ('Shield Throw', 'Smash', 'Traveling Knife'),
    "Gladiator's Tenacity": ('Torchbearer', "Ulfsild's Contingency"),
    'Growing Impact': ("Ulfsild's Contingency",),
    "Hunter's Snare": ('Elemental Explosion', "Mender's Bond", 'Traveling Knife', 'Vault', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency", 'Trample'),
    'Immobilizing Strike': ('Elemental Explosion', 'Smash', 'Trample'),
    "Knight's Valor": ("Mender's Bond", 'Shield Throw'),
    'Leeching Thirst': ('Smash', 'Traveling Knife'),
    'Lingering Torment': ('Elemental Explosion', 'Shield Throw', 'Smash', 'Traveling Knife', 'Vault', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency", 'Trample'),
    "Sage's Remedy": ("Mender's Bond", 'Shield Throw', 'Smash', 'Vault', 'Wield Soul', 'Soul Burst', "Ulfsild's Contingency", 'Banner Bearer'),
    "Thief's Swiftness": ('Shield Throw', 'Vault', 'Banner Bearer', 'Trample'),
    "Warmage's Defense": ('Elemental Explosion', "Mender's Bond", 'Traveling Knife', 'Banner Bearer'),
    "Warrior's Opportunity": ('Traveling Knife', 'Torchbearer', "Ulfsild's Contingency", 'Trample'),
    "Wayfarer's Mastery": ('Shield Throw', 'Smash', 'Traveling Knife', 'Vault', 'Banner Bearer', 'Trample')
}

AFFIX_COMPATIBILITY: dict[str, tuple[str, ...]] = {
    'Berserk': ('Smash', 'Traveling Knife', 'Banner Bearer'),
    'Breach': ("Mender's Bond", 'Smash', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency"),
    'Brittle': ('Elemental Explosion', "Mender's Bond"),
    'Brutality and Sorcery': ('Elemental Explosion', 'Wield Soul', 'Banner Bearer'),
    'Courage': ("Mender's Bond", 'Soul Burst', 'Banner Bearer'),
    'Cowardice': ('Elemental Explosion', 'Shield Throw', 'Wield Soul', 'Torchbearer', 'Trample'),
    'Defile': ('Elemental Explosion', 'Wield Soul', 'Trample'),
    'Empower': ("Mender's Bond", 'Wield Soul'),
    'Enervation': ('Elemental Explosion', 'Shield Throw', "Ulfsild's Contingency"),
    'Evasion': ('Shield Throw', 'Vault', 'Torchbearer'),
    'Expedition': ('Smash', 'Traveling Knife', 'Vault', 'Soul Burst', 'Trample'),
    'Force': ('Smash', 'Vault', "Ulfsild's Contingency"),
    'Heroism': ("Mender's Bond", 'Torchbearer', 'Banner Bearer', 'Trample'),
    'Intellect and Endurance': ("Mender's Bond", 'Wield Soul', 'Soul Burst', "Ulfsild's Contingency", 'Banner Bearer'),
    'Interrupt': ('Shield Throw', 'Smash', 'Soul Burst'),
    'Lifesteal': ('Elemental Explosion', 'Traveling Knife', 'Vault'),
    'Magickasteal': ('Elemental Explosion', 'Soul Burst', "Ulfsild's Contingency"),
    'Maim': ("Mender's Bond", 'Shield Throw', 'Smash', 'Traveling Knife', 'Vault', 'Soul Burst'),
    'Mangle': ('Smash', 'Torchbearer', 'Trample'),
    'Off Balance': ('Elemental Explosion', 'Shield Throw', 'Traveling Knife', 'Vault', 'Trample'),
    'Protection': ("Mender's Bond", "Ulfsild's Contingency", 'Banner Bearer'),
    'Resolve': ('Shield Throw', 'Wield Soul', 'Soul Burst', 'Torchbearer', "Ulfsild's Contingency", 'Banner Bearer'),
    'Savagery and Prophecy': ('Traveling Knife', 'Vault', 'Banner Bearer', 'Trample'),
    'Uncertainty': ('Torchbearer', 'Traveling Knife'),
    'Vitality': ("Mender's Bond", 'Shield Throw', 'Smash', 'Wield Soul', 'Torchbearer'),
    'Vulnerability': ('Traveling Knife', 'Vault', "Ulfsild's Contingency", 'Trample')
}

# Result display names are determined by Grimoire + Focus. Only mappings
# independently verified should be added here. Never synthesize names.
RESULT_NAMES: dict[tuple[str, str], str] = {
    ('Soul Burst', 'Damage Shield'): 'Warding Burst',
}


def grimoire_names() -> list[str]:
    return list(GRIMOIRE_SKILL_LINES)


def compatible_focus(grimoire: str) -> list[str]:
    return _compatible(FOCUS_COMPATIBILITY, grimoire)


def compatible_signature(grimoire: str) -> list[str]:
    return _compatible(SIGNATURE_COMPATIBILITY, grimoire)


def compatible_affix(grimoire: str) -> list[str]:
    return _compatible(AFFIX_COMPATIBILITY, grimoire)


def result_name(grimoire: str, focus: str) -> str:
    return RESULT_NAMES.get((str(grimoire).strip(), str(focus).strip()), '')


def skill_line_for_grimoire(grimoire: str) -> str:
    return GRIMOIRE_SKILL_LINES.get(str(grimoire).strip(), '')


def is_grimoire_compatible(script_type: str, script_name: str, grimoire: str) -> bool:
    maps = {
        'focus': FOCUS_COMPATIBILITY,
        'signature': SIGNATURE_COMPATIBILITY,
        'affix': AFFIX_COMPATIBILITY,
    }
    mapping = maps.get(str(script_type).strip().casefold())
    if mapping is None:
        return False
    return str(grimoire).strip() in mapping.get(str(script_name).strip(), ())


def _compatible(mapping: dict[str, tuple[str, ...]], grimoire: str) -> list[str]:
    target = str(grimoire).strip()
    return sorted(
        (name for name, grimoires in mapping.items() if target in grimoires),
        key=str.casefold,
    )
