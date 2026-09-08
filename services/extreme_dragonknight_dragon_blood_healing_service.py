from __future__ import annotations

from dataclasses import dataclass
import re

from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeDragonknightDragonBloodHealingResult:
    multiplier: float
    unresolved: tuple[str, ...]


class ExtremeDragonknightDragonBloodHealingService:
    """Resolve reviewed U50 Dragon Blood-family missing-health scaling.

    The base Dragon Blood ability and Blood of the Green Dragon are
    single-recipient self-heals that scale from Max Health. Under reviewed U50
    semantics, the direct heal increases by up to 50% in proportion to the
    caster's missing Health. This resolver models only that missing-health
    modifier; canonical coefficient math remains responsible for the underlying
    Max-Health-scaled heal value.

    Blood of the Elder Dragon (legacy Coagulating Blood) is deliberately excluded
    here because its cast contains distinct self and nearby-ally healing. The
    Extreme recipient-scope guard blocks that morph until coefficient recipient
    identity is canonical.

    Explicit ClassSkillLines are authoritative for subclass snapshots. A pure
    Dragonknight implicitly owns Draconic Power only when no explicit route is
    supplied; another base class may use the family through an explicit Draconic
    Power subclass route.
    """

    DRACONIC_POWER_ID = "draconic_power"
    MAX_HEALING_BONUS = 0.50
    SINGLE_RECIPIENT_FAMILY = frozenset({"dragon blood", "blood of the green dragon"})

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def draconic_power_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.DRACONIC_POWER_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "dragonknight"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        ability_name: str,
        caster_health_fraction: float | None,
    ) -> ExtremeDragonknightDragonBloodHealingResult:
        normalized = " ".join(str(ability_name or "").strip().casefold().split())
        if normalized not in self.SINGLE_RECIPIENT_FAMILY:
            return ExtremeDragonknightDragonBloodHealingResult(1.0, ())
        if not self.draconic_power_equipped(build):
            return ExtremeDragonknightDragonBloodHealingResult(1.0, ())
        if caster_health_fraction is None:
            return ExtremeDragonknightDragonBloodHealingResult(
                1.0,
                ("Dragon Blood missing-health scaling requires explicit caster Health fraction",),
            )

        value = float(caster_health_fraction)
        if not 0.0 <= value <= 1.0:
            raise ValueError("caster_health_fraction must be between 0 and 1")

        missing_health_fraction = 1.0 - value
        return ExtremeDragonknightDragonBloodHealingResult(
            multiplier=1.0 + self.MAX_HEALING_BONUS * missing_health_fraction,
            unresolved=(),
        )
