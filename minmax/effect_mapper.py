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

        "healing_done": StatId.HEALING_DONE,
    }

    @classmethod
    def to_stat(cls, effect_type: str) -> StatId:
        try:
            return cls.STAT_MAP[effect_type]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported engine stat effect type: "
                f"{effect_type!r}"
            ) from exc

    @staticmethod
    def to_unit(unit: str) -> EffectUnit:
        try:
            return EffectUnit(unit)
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