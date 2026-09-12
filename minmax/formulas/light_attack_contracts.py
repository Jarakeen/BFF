"""Dependency contracts for light-attack formulas.

These contracts describe WHAT each formula requires and WHERE each input
belongs in the calculation pipeline.

They do not perform calculations.
They do not resolve database effects.
They are architectural metadata.
"""

LIGHT_ATTACK_CONTRACTS = {
    "flame_staff": {
        "formula": "calculate_la_flame_staff",
        "inputs": {
            "magicka": {
                "layer": "core",
                "application": "base",
            },
            "stamina": {
                "layer": "core",
                "application": "base",
            },
            "la_flame_spell_damage": {
                "layer": "derived",
                "application": "base",
            },
            "la_flame_weapon_damage": {
                "layer": "derived",
                "application": "base",
            },
            "skill2_la_damage": {
                "layer": "modifier",
                "application": "additive_to_base",
            },
            "cp_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "skill_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "set_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "flame_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "direct_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "single_target_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
        },
    },

    "frost_staff": {
        "formula": "calculate_la_frost_staff",
        "inputs": {
            "magicka": {
                "layer": "core",
                "application": "base",
            },
            "stamina": {
                "layer": "core",
                "application": "base",
            },
            "la_frost_spell_damage": {
                "layer": "derived",
                "application": "base",
            },
            "la_frost_weapon_damage": {
                "layer": "derived",
                "application": "base",
            },
            "skill2_la_damage": {
                "layer": "modifier",
                "application": "additive_to_base",
            },
            "cp_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "skill_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "set_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "frost_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "direct_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "single_target_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
        },
    },

    "shock_staff": {
        "formula": "calculate_la_shock_staff",
        "inputs": {
            "magicka": {
                "layer": "core",
                "application": "base",
            },
            "stamina": {
                "layer": "core",
                "application": "base",
            },
            "la_shock_spell_damage": {
                "layer": "derived",
                "application": "base",
            },
            "la_shock_weapon_damage": {
                "layer": "derived",
                "application": "base",
            },
            "skill2_la_damage": {
                "layer": "modifier",
                "application": "additive_to_base",
            },
            "cp_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "skill_ha_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "set_ha_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "buff_empower": {
                "layer": "buff",
                "application": "multiplier",
            },
            "shock_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "single_target_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "dot_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
        },
    },

    "bow": {
        "formula": "calculate_la_bow",
        "inputs": {
            "magicka": {
                "layer": "core",
                "application": "base",
            },
            "stamina": {
                "layer": "core",
                "application": "base",
            },
            "la_physical_weapon_damage": {
                "layer": "derived",
                "application": "base",
            },
            "la_physical_spell_damage": {
                "layer": "derived",
                "application": "base",
            },
            "skill2_la_damage": {
                "layer": "modifier",
                "application": "additive_to_base",
            },
            "cp_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "skill_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "set_la_damage": {
                "layer": "modifier",
                "application": "multiplier",
            },
            "bow_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "physical_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "direct_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "single_target_damage_done": {
                "layer": "damage_done",
                "application": "multiplier",
            },
            "skill_line_damage_bow": {
                "layer": "damage_done",
                "application": "multiplier",
            },
        },
    },
}
