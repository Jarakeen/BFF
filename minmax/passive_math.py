from __future__ import annotations


# Warden class passives, max rank, current values from canonical passive data.
WARDEN_FLOURISH_RECOVERY_PERCENT = 0.20
WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED = 0.05
WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED = 1240.0
WARDEN_PIERCING_COLD_BLOCK_MITIGATION_PERCENT = 0.08
WARDEN_PIERCING_COLD_FROST_DAMAGE_PERCENT = 0.15


# Undaunted Mettle, max rank.
UNDAUNTED_METTLE_RESOURCE_PERCENT_PER_ARMOR_TYPE = 0.02


# Mages Guild / Fighters Guild standing passives, max rank.
MAGES_GUILD_MAGICKA_CONTROLLER_PERCENT_PER_SLOTTED = 0.02
FIGHTERS_GUILD_SLAYER_WEAPON_SPELL_DAMAGE_PERCENT_PER_SLOTTED = 0.03


# Light Armor, max-rank passive values per equipped piece.
LIGHT_ARMOR_PENETRATION_PER_PIECE = 939.0
LIGHT_ARMOR_MAGICKA_RECOVERY_PERCENT_PER_PIECE = 0.04
LIGHT_ARMOR_CRITICAL_RATING_PER_PIECE = 219.0
LIGHT_ARMOR_SPELL_RESISTANCE_PER_PIECE = 726.0


# Medium Armor, max-rank passive values per equipped piece.
MEDIUM_ARMOR_WEAPON_SPELL_DAMAGE_PERCENT_PER_PIECE = 0.02
MEDIUM_ARMOR_CRIT_DAMAGE_HEALING_PERCENT_PER_PIECE = 0.02
MEDIUM_ARMOR_STAMINA_RECOVERY_PERCENT_PER_PIECE = 0.04


def _count(value: int) -> int:
    return max(0, int(value))


def warden_flourish_recovery_percent(slotted_animal_companion_abilities: int) -> float:
    """Return Flourish's recovery bonus for the active bar.

    Max-rank Flourish grants +20% Magicka and Stamina Recovery only while at
    least one Animal Companions ability is slotted on the active bar.
    """
    return WARDEN_FLOURISH_RECOVERY_PERCENT if _count(slotted_animal_companion_abilities) > 0 else 0.0


def warden_advanced_species_crit_damage(slotted_animal_companion_abilities: int) -> float:
    return _count(slotted_animal_companion_abilities) * WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED


def warden_frozen_armor_resistance(slotted_winters_embrace_abilities: int) -> float:
    return _count(slotted_winters_embrace_abilities) * WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED


def undaunted_mettle_resource_percent(equipped_armor_type_count: int) -> float:
    # ESO has only three armor types; clamp rather than allowing malformed build
    # data to create impossible passive values.
    return min(_count(equipped_armor_type_count), 3) * UNDAUNTED_METTLE_RESOURCE_PERCENT_PER_ARMOR_TYPE


def mages_guild_magicka_controller_percent(slotted_mages_guild_abilities: int) -> float:
    return _count(slotted_mages_guild_abilities) * MAGES_GUILD_MAGICKA_CONTROLLER_PERCENT_PER_SLOTTED


def fighters_guild_slayer_weapon_spell_damage_percent(slotted_fighters_guild_abilities: int) -> float:
    return _count(slotted_fighters_guild_abilities) * FIGHTERS_GUILD_SLAYER_WEAPON_SPELL_DAMAGE_PERCENT_PER_SLOTTED


def light_armor_penetration(piece_count: int) -> float:
    return _count(piece_count) * LIGHT_ARMOR_PENETRATION_PER_PIECE


def light_armor_magicka_recovery_percent(piece_count: int) -> float:
    return _count(piece_count) * LIGHT_ARMOR_MAGICKA_RECOVERY_PERCENT_PER_PIECE


def light_armor_critical_rating(piece_count: int) -> float:
    return _count(piece_count) * LIGHT_ARMOR_CRITICAL_RATING_PER_PIECE


def light_armor_spell_resistance(piece_count: int) -> float:
    return _count(piece_count) * LIGHT_ARMOR_SPELL_RESISTANCE_PER_PIECE


def medium_armor_weapon_spell_damage_percent(piece_count: int) -> float:
    return _count(piece_count) * MEDIUM_ARMOR_WEAPON_SPELL_DAMAGE_PERCENT_PER_PIECE


def medium_armor_crit_damage_healing_percent(piece_count: int) -> float:
    return _count(piece_count) * MEDIUM_ARMOR_CRIT_DAMAGE_HEALING_PERCENT_PER_PIECE


def medium_armor_stamina_recovery_percent(piece_count: int) -> float:
    return _count(piece_count) * MEDIUM_ARMOR_STAMINA_RECOVERY_PERCENT_PER_PIECE
