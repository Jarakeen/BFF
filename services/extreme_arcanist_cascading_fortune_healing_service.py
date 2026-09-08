from __future__ import annotations

from dataclasses import dataclass
import re

from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeArcanistCascadingFortuneHealingResult:
    multiplier: float
    unresolved: tuple[str, ...]


class ExtremeArcanistCascadingFortuneHealingService:
    """Resolve Cascading Fortune's reviewed wounded-target healing modifier.

    Under reviewed U50 semantics, Cascading Fortune heals for up to 50% more in
    proportion to the severity of the target's wounds. This service models that
    wording linearly against missing-health fraction, matching the same explicit
    target-health treatment used by other proportional emergency-heal mechanics.

    The modifier belongs to Cascading Fortune itself. It must never increase
    other Curative Runeforms heals merely because the route is equipped.
    Explicit ``ClassSkillLines`` remain authoritative for subclass snapshots.
    """

    ABILITY_NAME = "Cascading Fortune"
    CURATIVE_RUNEFORMS_ID = "curative_runeforms"
    MAX_HEALING_BONUS = 0.50

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def curative_runeforms_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.CURATIVE_RUNEFORMS_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "arcanist"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        ability_name: str,
        target_health_fraction: float | None,
    ) -> ExtremeArcanistCascadingFortuneHealingResult:
        name = str(ability_name or "").strip()
        if name.casefold() != self.ABILITY_NAME.casefold():
            return ExtremeArcanistCascadingFortuneHealingResult(1.0, ())
        if not self.curative_runeforms_equipped(build):
            return ExtremeArcanistCascadingFortuneHealingResult(1.0, ())
        if target_health_fraction is None:
            return ExtremeArcanistCascadingFortuneHealingResult(1.0, ())

        target_health_fraction = float(target_health_fraction)
        if not 0.0 <= target_health_fraction <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")

        missing_health_fraction = 1.0 - target_health_fraction
        return ExtremeArcanistCascadingFortuneHealingResult(
            multiplier=1.0 + self.MAX_HEALING_BONUS * missing_health_fraction,
            unresolved=(),
        )
