from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeSorcererBloodMagicResult:
    branch: str | None
    self_heal: float | None
    resource_stat: str | None
    resource_percent: float
    duration_seconds: float | None
    unresolved: tuple[str, ...]


class ExtremeSorcererBloodMagicService:
    """Resolve the two reviewed live-U50 Blood Magic runtime branches.

    Blood Magic triggers from a costed Dark Magic ability cast. At max rank, a
    caster below full Health receives a self-heal that scales from Max Health; at
    full Health, the higher of Max Magicka or Max Stamina is increased by 10% for
    10 seconds. This service resolves the branch and magnitude but deliberately
    does not mutate a calculation context. The conditional optimizer must consume
    the returned resource window explicitly before Dark Magic can be called fully
    implemented by the family coverage audit.

    The live rank-2 tooltip is 1600 Health on the canonical 16000-health baseline,
    which corresponds to 10% Max Health. That proportional relationship is used
    here so the passive self-heal follows canonical character Max Health.
    """

    PASSIVE_NAME = "Blood Magic"
    DARK_MAGIC_ID = "dark_magic"
    SELF_HEAL_MAX_HEALTH_RATIO = 0.10
    RESOURCE_PERCENT = 0.10
    RESOURCE_DURATION_SECONDS = 10.0

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
    def dark_magic_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.DARK_MAGIC_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "sorcerer"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        context: BuildCalculationContext,
        trigger_ability_name: str,
        trigger_ability_has_cost: bool,
        caster_health_fraction: float,
    ) -> ExtremeSorcererBloodMagicResult:
        health_fraction = float(caster_health_fraction)
        if not 0.0 <= health_fraction <= 1.0:
            raise ValueError("caster_health_fraction must be between 0 and 1")

        if not self.dark_magic_equipped(build):
            return ExtremeSorcererBloodMagicResult(None, None, None, 0.0, None, ())

        name = str(trigger_ability_name or "").strip()
        if not name:
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                ("Blood Magic requires an explicit triggering ability",),
            )
        skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
        if skill_line is None:
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                (f"Blood Magic trigger skill line is unresolved for ability: {name}",),
            )
        if self._line_id(skill_line) != self.DARK_MAGIC_ID:
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                (f"Blood Magic requires a Dark Magic triggering ability: {name}",),
            )
        if not bool(trigger_ability_has_cost):
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                ("Blood Magic requires a triggering Dark Magic ability with a cost",),
            )

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                ("Blood Magic passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                ("Passive rank is not recorded for character: Blood Magic",),
            )
        if int(rank) == 0:
            return ExtremeSorcererBloodMagicResult(None, None, None, 0.0, None, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                ("Passive max rank is not available in canonical data: Blood Magic",),
            )
        if int(rank) != int(maximum):
            return ExtremeSorcererBloodMagicResult(
                None,
                None,
                None,
                0.0,
                None,
                (f"Partial passive rank is not yet modeled: Blood Magic {rank}/{maximum}",),
            )

        if health_fraction < 1.0:
            return ExtremeSorcererBloodMagicResult(
                branch="self_heal",
                self_heal=float(context.character_state.max_health)
                * self.SELF_HEAL_MAX_HEALTH_RATIO,
                resource_stat=None,
                resource_percent=0.0,
                duration_seconds=None,
                unresolved=(),
            )

        magicka = float(context.character_state.max_magicka)
        stamina = float(context.character_state.max_stamina)
        if abs(magicka - stamina) <= 1e-9:
            return ExtremeSorcererBloodMagicResult(
                branch="resource_window",
                self_heal=None,
                resource_stat=None,
                resource_percent=self.RESOURCE_PERCENT,
                duration_seconds=self.RESOURCE_DURATION_SECONDS,
                unresolved=(
                    "Blood Magic higher-resource branch is ambiguous because Max Magicka and Max Stamina are equal",
                ),
            )

        return ExtremeSorcererBloodMagicResult(
            branch="resource_window",
            self_heal=None,
            resource_stat="max_magicka" if magicka > stamina else "max_stamina",
            resource_percent=self.RESOURCE_PERCENT,
            duration_seconds=self.RESOURCE_DURATION_SECONDS,
            unresolved=(),
        )
