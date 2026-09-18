from __future__ import annotations

"""Audit legal weapon configurations and weapon-passive coverage for Extreme H1.

This service owns denominator proof, not healing arithmetic. It enumerates every
legal ESO bar weapon configuration represented by the canonical WeaponType model,
then reconciles every canonical weapon passive in eso.db against the reviewed
weapon-passive classification ledger.

The current H1 optimizer already enforces weapon-skill legality for the selected
heal and evaluates reviewed Restoration Staff healing passives. This audit exposes
what remains before the broader weapon-configuration/passive dimension can be
called closed instead of merely useful.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.weapon_type import (
    WeaponSkillLine,
    WeaponType,
    resolve_weapon_skill_line,
)
from minmax.weapon_passive_classification import VERIFIED_WEAPON_PASSIVE_RULES
from services.extreme_skill_universe_service import (
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


@dataclass(frozen=True)
class ExtremeActualHealWeaponConfiguration:
    main_hand: WeaponType
    off_hand: WeaponType
    skill_line: WeaponSkillLine

    @property
    def key(self) -> str:
        return f"{self.main_hand.value}+{self.off_hand.value}"


@dataclass(frozen=True)
class ExtremeActualHealWeaponDenominator:
    legal_bar_configurations: tuple[ExtremeActualHealWeaponConfiguration, ...]
    canonical_weapon_passives: tuple[str, ...]
    reviewed_weapon_passives: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def legal_bar_configuration_count(self) -> int:
        return len(self.legal_bar_configurations)

    @property
    def legal_two_bar_configuration_count(self) -> int:
        count = self.legal_bar_configuration_count
        return count * count

    @property
    def passive_denominator_proven(self) -> bool:
        return bool(self.canonical_weapon_passives and not self.unresolved)

    @property
    def configuration_denominator_proven(self) -> bool:
        return self.legal_bar_configuration_count > 0

    @property
    def denominator_proven(self) -> bool:
        return self.configuration_denominator_proven and self.passive_denominator_proven


class ExtremeActualHealWeaponDenominatorService:
    def __init__(
        self,
        database_path: str | Path,
        *,
        universe_service: ExtremeSkillUniverseService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.universe = universe_service or ExtremeSkillUniverseService(self.database_path)

    @staticmethod
    def legal_bar_configurations() -> tuple[ExtremeActualHealWeaponConfiguration, ...]:
        physical = tuple(
            weapon_type
            for weapon_type in WeaponType
            if weapon_type is not WeaponType.NONE
        )
        configurations: list[ExtremeActualHealWeaponConfiguration] = []
        for main_hand in physical:
            for off_hand in (WeaponType.NONE, *physical):
                try:
                    line = resolve_weapon_skill_line(main_hand, off_hand)
                except ValueError:
                    continue
                configurations.append(
                    ExtremeActualHealWeaponConfiguration(
                        main_hand=main_hand,
                        off_hand=off_hand,
                        skill_line=line,
                    )
                )
        return tuple(
            sorted(
                configurations,
                key=lambda row: (
                    row.skill_line.value,
                    row.main_hand.value,
                    row.off_hand.value,
                ),
            )
        )

    def build(self) -> ExtremeActualHealWeaponDenominator:
        configurations = self.legal_bar_configurations()

        canonical_rows = tuple(
            row
            for row in self.universe.passives()
            if row.domain is ExtremeSkillDomain.WEAPON
        )
        canonical = tuple(
            sorted(
                {
                    f"{row.skill_line} :: {row.name}"
                    for row in canonical_rows
                    if row.skill_line and row.name
                },
                key=str.casefold,
            )
        )
        reviewed = tuple(
            sorted(
                {
                    f"{rule.skill_line} :: {rule.passive}"
                    for rule in VERIFIED_WEAPON_PASSIVE_RULES
                },
                key=str.casefold,
            )
        )

        canonical_keys = {
            value.casefold(): value
            for value in canonical
        }
        reviewed_keys = {
            value.casefold(): value
            for value in reviewed
        }

        unresolved: list[str] = []
        for key, display in canonical_keys.items():
            if key not in reviewed_keys:
                unresolved.append(
                    f"canonical weapon passive has no reviewed H1 disposition: {display}"
                )
        for key, display in reviewed_keys.items():
            if key not in canonical_keys:
                unresolved.append(
                    f"reviewed weapon-passive rule is stale or absent from canonical data: {display}"
                )

        return ExtremeActualHealWeaponDenominator(
            legal_bar_configurations=configurations,
            canonical_weapon_passives=canonical,
            reviewed_weapon_passives=reviewed,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeActualHealWeaponConfiguration",
    "ExtremeActualHealWeaponDenominator",
    "ExtremeActualHealWeaponDenominatorService",
]
