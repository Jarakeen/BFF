from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeTemplarLightWeaverResult:
    ally_ultimate_granted: int
    automatic_block_active: bool
    automatic_block_seconds: float
    automatic_block_cooldown_seconds: float
    unresolved: tuple[str, ...]


class ExtremeTemplarLightWeaverService:
    """Resolve reviewed Templar Light Weaver runtime effects.

    Light Weaver has two independent branches and neither changes the healing
    amount itself:

    * healing an ally below 50% Health with a Restoring Light ability grants
      that ally 1 Ultimate at rank 1 or 2 Ultimate at rank 2;
    * activating an ability with a cast or channel time while in combat grants
      two seconds of automatic no-cost blocking, with a 30-second cooldown at
      rank 1 and a 15-second cooldown at rank 2.

    The caller supplies the relevant event facts explicitly. This resolver never
    invents ally identity, target Health, cast/channel semantics, combat state,
    or prior proc timing. Restoring Light ownership follows the same subclass-
    aware route rule as the other Templar Extreme services.
    """

    PASSIVE_NAME = "Light Weaver"
    RESTORING_LIGHT_ID = "restoring_light"
    ULTIMATE_BY_RANK = {1: 1, 2: 2}
    BLOCK_SECONDS = 2.0
    BLOCK_COOLDOWN_BY_RANK = {1: 30.0, 2: 15.0}

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_line_repository: SkillLineRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path or get_data_dir() / "eso.db")
        self.skill_line_repository = skill_line_repository or SkillLineRepository(
            self.database_path
        )

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def restoring_light_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.RESTORING_LIGHT_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "templar"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        ability_name: str = "",
        target_health_fraction: float | None = None,
        target_is_ally: bool = False,
        activation_has_cast_or_channel_time: bool = False,
        in_combat: bool = False,
        activation_time_seconds: float | None = None,
        previous_automatic_block_proc_time_seconds: float | None = None,
    ) -> ExtremeTemplarLightWeaverResult:
        base = ExtremeTemplarLightWeaverResult(0, False, 0.0, 0.0, ())
        if not self.restoring_light_equipped(build):
            return base

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeTemplarLightWeaverResult(
                0, False, 0.0, 0.0, ("Light Weaver passive rank is not recorded",)
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeTemplarLightWeaverResult(
                0,
                False,
                0.0,
                0.0,
                ("Passive rank is not recorded for character: Light Weaver",),
            )
        if rank == 0:
            return base

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeTemplarLightWeaverResult(
                0,
                False,
                0.0,
                0.0,
                ("Passive max rank is not available in canonical data: Light Weaver",),
            )
        if rank not in self.ULTIMATE_BY_RANK or rank > maximum:
            return ExtremeTemplarLightWeaverResult(
                0,
                False,
                0.0,
                0.0,
                (f"Unsupported passive rank: Light Weaver {rank}/{maximum}",),
            )

        ultimate = 0
        if target_health_fraction is not None:
            health = float(target_health_fraction)
            if not 0.0 <= health <= 1.0:
                raise ValueError("target_health_fraction must be between 0 and 1")
            if target_is_ally and health < 0.50 and str(ability_name or "").strip():
                ability_line = self.skill_line_repository.skill_line_for_ability_name(
                    str(ability_name).strip()
                )
                if ability_line is None:
                    return ExtremeTemplarLightWeaverResult(
                        0,
                        False,
                        0.0,
                        self.BLOCK_COOLDOWN_BY_RANK[rank],
                        (
                            "Light Weaver ability family: could not resolve canonical skill line "
                            f"for ability {str(ability_name).strip()!r}",
                        ),
                    )
                if self._line_id(ability_line) == self.RESTORING_LIGHT_ID:
                    ultimate = self.ULTIMATE_BY_RANK[rank]

        automatic_block_active = False
        if activation_has_cast_or_channel_time and in_combat:
            if activation_time_seconds is None:
                return ExtremeTemplarLightWeaverResult(
                    ultimate,
                    False,
                    0.0,
                    self.BLOCK_COOLDOWN_BY_RANK[rank],
                    ("Light Weaver automatic block requires activation_time_seconds",),
                )
            activation = float(activation_time_seconds)
            if not math.isfinite(activation) or activation < 0.0:
                raise ValueError(
                    "activation_time_seconds must be a finite non-negative value"
                )
            previous = previous_automatic_block_proc_time_seconds
            if previous is not None:
                previous = float(previous)
                if not math.isfinite(previous) or previous < 0.0:
                    raise ValueError(
                        "previous_automatic_block_proc_time_seconds must be a finite non-negative value"
                    )
                if previous > activation:
                    raise ValueError(
                        "previous Light Weaver proc cannot occur after activation"
                    )
            cooldown = self.BLOCK_COOLDOWN_BY_RANK[rank]
            automatic_block_active = (
                previous is None or activation - previous >= cooldown
            )

        return ExtremeTemplarLightWeaverResult(
            ally_ultimate_granted=ultimate,
            automatic_block_active=automatic_block_active,
            automatic_block_seconds=self.BLOCK_SECONDS if automatic_block_active else 0.0,
            automatic_block_cooldown_seconds=self.BLOCK_COOLDOWN_BY_RANK[rank],
            unresolved=(),
        )
