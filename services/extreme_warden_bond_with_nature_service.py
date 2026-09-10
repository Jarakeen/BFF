from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_trigger_relationship import SkillComponentTriggerType
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeWardenBondWithNatureResult:
    base_self_heal: float | None
    passive_rank: int | None
    trigger_event: RuntimeEvent | None
    unresolved: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return self.base_self_heal is not None and not self.unresolved


class ExtremeWardenBondWithNatureService:
    """Resolve live-U50 Bond with Nature trigger legality and base self-heal.

    Bond with Nature heals the caster whenever one of their Animal Companions
    skills ends. Rank I/II base values are 765/1530 Health. This service owns only
    passive/subclass/trigger legality and the unmodified base amount; canonical
    Healing Done, Healing Taken, Healing Received and Critical Healing are applied
    by the dedicated healing-event adapter.
    """

    PASSIVE_NAME = "Bond with Nature"
    ANIMAL_COMPANIONS_ID = "animal_companions"
    BASE_HEAL_BY_RANK = {1: 765.0, 2: 1530.0}
    EFFECT_ENDED_TRIGGER = SkillComponentTriggerType.EFFECT_ENDED.value

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
    def animal_companions_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.ANIMAL_COMPANIONS_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "warden"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        trigger_event: RuntimeEvent,
    ) -> ExtremeWardenBondWithNatureResult:
        if not self.animal_companions_equipped(build):
            return ExtremeWardenBondWithNatureResult(
                None,
                progression.passive_rank(self.PASSIVE_NAME),
                trigger_event,
                ("Bond with Nature requires an equipped Animal Companions class line",),
            )

        if trigger_event.trigger != self.EFFECT_ENDED_TRIGGER:
            return ExtremeWardenBondWithNatureResult(
                None,
                progression.passive_rank(self.PASSIVE_NAME),
                trigger_event,
                ("Bond with Nature requires a canonical effect_ended runtime event",),
            )

        skill_line = self.skill_line_repository.skill_line_for_ability_name(
            trigger_event.source
        )
        if skill_line is None:
            return ExtremeWardenBondWithNatureResult(
                None,
                progression.passive_rank(self.PASSIVE_NAME),
                trigger_event,
                (
                    "Bond with Nature could not resolve the triggering ability's canonical skill line: "
                    f"{trigger_event.source}",
                ),
            )
        if self._line_id(skill_line) != self.ANIMAL_COMPANIONS_ID:
            return ExtremeWardenBondWithNatureResult(
                None,
                progression.passive_rank(self.PASSIVE_NAME),
                trigger_event,
                ("Bond with Nature trigger must come from an Animal Companions ability",),
            )

        if progression.passive_ranks is None:
            return ExtremeWardenBondWithNatureResult(
                None,
                None,
                trigger_event,
                ("Bond with Nature passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeWardenBondWithNatureResult(
                None,
                None,
                trigger_event,
                ("Passive rank is not recorded for character: Bond with Nature",),
            )
        if rank == 0:
            return ExtremeWardenBondWithNatureResult(None, 0, trigger_event, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeWardenBondWithNatureResult(
                None,
                rank,
                trigger_event,
                ("Passive max rank is not available in canonical data: Bond with Nature",),
            )
        if rank < 0 or rank > maximum or rank not in self.BASE_HEAL_BY_RANK:
            return ExtremeWardenBondWithNatureResult(
                None,
                rank,
                trigger_event,
                (f"Unsupported passive rank for Bond with Nature: {rank}/{maximum}",),
            )

        return ExtremeWardenBondWithNatureResult(
            self.BASE_HEAL_BY_RANK[rank],
            rank,
            trigger_event,
            (),
        )
