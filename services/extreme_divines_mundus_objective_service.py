from __future__ import annotations

"""Project legal Divines amplification into Extreme Mundus objective scoring.

This layer deliberately answers a narrow question: given a fixed legal set of
Divines sources, what multiplier applies to the chosen Mundus and what does that
Mundus contribute to a reviewed Extreme objective?

It does *not* claim that the configuration is the best full build. Replacing a
piece trait with Divines has an opportunity cost, and using a Divines shield can
change weapon/base-stat/passive legality. Those choices belong to higher-level
joint optimization.
"""

from dataclasses import dataclass

from minmax.mundus_repository import MundusRepository
from minmax.static_build_inputs import DIVINES_PERCENT_BY_QUALITY
from services.extreme_mundus_objective_service import (
    ExtremeMundusObjectiveCandidate,
    ExtremeMundusObjectiveService,
)


@dataclass(frozen=True)
class ExtremeDivinesMundusConfiguration:
    armor_divines_count: int
    shield_divines: bool
    multiplier: float

    @property
    def divines_source_count(self) -> int:
        return int(self.armor_divines_count) + int(bool(self.shield_divines))

    @property
    def label(self) -> str:
        shield = " + shield" if self.shield_divines else ""
        return f"{self.armor_divines_count} armor Divines{shield}"


@dataclass(frozen=True)
class ExtremeDivinesMundusObjectiveCandidate:
    configuration: ExtremeDivinesMundusConfiguration
    mundus: ExtremeMundusObjectiveCandidate

    @property
    def objective_key(self) -> str:
        return self.mundus.objective_key

    @property
    def projected_delta(self) -> float | None:
        return self.mundus.projected_delta


class ExtremeDivinesMundusObjectiveService:
    """Resolve exact Gold-Divines amplification without choosing the whole build."""

    ARMOR_SLOTS = 7
    GOLD_DIVINES_RATIO = float(DIVINES_PERCENT_BY_QUALITY["gold"]) / 100.0

    @classmethod
    def configuration(
        cls,
        *,
        armor_divines_count: int,
        shield_divines: bool = False,
    ) -> ExtremeDivinesMundusConfiguration:
        count = int(armor_divines_count)
        if count < 0 or count > cls.ARMOR_SLOTS:
            raise ValueError("armor_divines_count must be between 0 and 7")
        source_count = count + int(bool(shield_divines))
        return ExtremeDivinesMundusConfiguration(
            armor_divines_count=count,
            shield_divines=bool(shield_divines),
            multiplier=1.0 + source_count * cls.GOLD_DIVINES_RATIO,
        )

    @classmethod
    def candidate_for_name(
        cls,
        repository: MundusRepository,
        mundus_name: str,
        objective_key: str,
        *,
        armor_divines_count: int,
        shield_divines: bool = False,
    ) -> ExtremeDivinesMundusObjectiveCandidate:
        config = cls.configuration(
            armor_divines_count=armor_divines_count,
            shield_divines=shield_divines,
        )
        mundus = ExtremeMundusObjectiveService.candidate_for_name(
            repository,
            mundus_name,
            objective_key,
            multiplier=config.multiplier,
        )
        return ExtremeDivinesMundusObjectiveCandidate(
            configuration=config,
            mundus=mundus,
        )

    @classmethod
    def best_mundus_for_configuration(
        cls,
        repository: MundusRepository,
        objective_key: str,
        *,
        armor_divines_count: int,
        shield_divines: bool = False,
    ) -> ExtremeDivinesMundusObjectiveCandidate | None:
        config = cls.configuration(
            armor_divines_count=armor_divines_count,
            shield_divines=shield_divines,
        )
        mundus = ExtremeMundusObjectiveService.best_for_objective(
            repository,
            objective_key,
            multiplier=config.multiplier,
        )
        if mundus is None:
            return None
        return ExtremeDivinesMundusObjectiveCandidate(
            configuration=config,
            mundus=mundus,
        )

    @classmethod
    def legal_configurations(
        cls,
        *,
        include_shield: bool,
    ) -> tuple[ExtremeDivinesMundusConfiguration, ...]:
        shield_states = (False, True) if include_shield else (False,)
        return tuple(
            cls.configuration(
                armor_divines_count=count,
                shield_divines=shield_divines,
            )
            for count in range(cls.ARMOR_SLOTS + 1)
            for shield_divines in shield_states
        )
