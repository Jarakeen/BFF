from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


class EffectMapper:

    STAT_MAP: dict[str, StatId] = {
        "maximum_health": StatId.MAX_HEALTH,
        "maximum_magicka": StatId.MAX_MAGICKA,
        "maximum_stamina": StatId.MAX_STAMINA,

        "max_health": StatId.MAX_HEALTH,
        "max_magicka": StatId.MAX_MAGICKA,
        "max_stamina": StatId.MAX_STAMINA,

        "health_recovery": StatId.HEALTH_RECOVERY,
        "magicka_recovery": StatId.MAGICKA_RECOVERY,
        "stamina_recovery": StatId.STAMINA_RECOVERY,

        "weapon_damage": StatId.WEAPON_DAMAGE,
        "spell_damage": StatId.SPELL_DAMAGE,

        "physical_resistance": StatId.PHYSICAL_RESISTANCE,
        "spell_resistance": StatId.SPELL_RESISTANCE,

        "physical_penetration": StatId.PHYSICAL_PENETRATION,
        "spell_penetration": StatId.SPELL_PENETRATION,

        "weapon_critical": StatId.WEAPON_CRITICAL,
        "spell_critical": StatId.SPELL_CRITICAL,
        "critical_chance": StatId.CRITICAL_CHANCE,
        "critical_damage": StatId.CRITICAL_DAMAGE,
        "critical_resistance": StatId.CRITICAL_RESISTANCE,

        "healing_done": StatId.HEALING_DONE,
        "healing_taken": StatId.HEALING_TAKEN,
    }

    @classmethod
    def to_stat(cls, effect_type: str) -> StatId:
        normalized = str(effect_type or "").strip().casefold()
        try:
            return cls.STAT_MAP[normalized]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported engine stat effect type: "
                f"{effect_type!r}"
            ) from exc

    @staticmethod
    def to_unit(unit: str) -> EffectUnit:
        normalized = str(unit or "").strip().casefold()
        try:
            return EffectUnit(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported effect unit: {unit!r}"
            ) from exc

    @classmethod
    def create_additive(
        cls,
        *,
        effect_type: str,
        value: float,
        unit: str,
        source: str,
    ) -> Effect:

        return Effect(
            kind=EffectKind.STAT,
            stat=cls.to_stat(effect_type),
            operation=EffectOperation.ADD,
            value=float(value),
            source=source,
            unit=cls.to_unit(unit),
        )
