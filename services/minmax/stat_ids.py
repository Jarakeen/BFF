from enum import Enum


class StatId(str, Enum):
    MAX_HEALTH = "max_health"
    MAX_MAGICKA = "max_magicka"
    MAX_STAMINA = "max_stamina"

    HEALTH_RECOVERY = "health_recovery"
    MAGICKA_RECOVERY = "magicka_recovery"
    STAMINA_RECOVERY = "stamina_recovery"

    WEAPON_DAMAGE = "weapon_damage"
    SPELL_DAMAGE = "spell_damage"

    PHYSICAL_RESISTANCE = "physical_resistance"
    SPELL_RESISTANCE = "spell_resistance"

    PHYSICAL_PENETRATION = "physical_penetration"
    SPELL_PENETRATION = "spell_penetration"

    WEAPON_CRITICAL = "weapon_critical"
    SPELL_CRITICAL = "spell_critical"

    CRITICAL_DAMAGE = "critical_damage"
    HEALING_DONE = "healing_done"