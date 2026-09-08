from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeTemplarIlluminateCombatStateResult:
    combat_state: CombatState
    minor_sorcery_active: bool
    unresolved: tuple[str, ...]


class ExtremeTemplarIlluminateCombatStateService:
    """Resolve reviewed U50 Templar Illuminate Minor Sorcery state.

    In U50, casting a Dawn's Wrath ability grants Minor Sorcery to the caster and
    group. Rank I lasts 10 seconds and Rank II lasts 20 seconds; the named buff's
    magnitude is unchanged, so an explicitly active window can be resolved at
    either learned rank without guessing duration. The caller must explicitly
    state that the Illuminate window is active. This service never invents a
    qualifying Dawn's Wrath cast merely because the line or passive is owned.

    Once legality is proven, Minor Sorcery is routed through ``CombatState`` so
    the canonical U50 named-buff layer owns the +10% Spell Damage semantics before
    healing coefficients are evaluated.
    """

    PASSIVE_NAME = "Illuminate"
    DAWNS_WRATH_ID = "dawns_wrath"

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
    def dawns_wrath_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.DAWNS_WRATH_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "templar"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        illuminate_window_active: bool = False,
    ) -> ExtremeTemplarIlluminateCombatStateResult:
        if not illuminate_window_active:
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=CombatState(),
                minor_sorcery_active=False,
                unresolved=(),
            )

        base_state = CombatState(in_combat=True)
        if not self.dawns_wrath_equipped(build):
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=base_state,
                minor_sorcery_active=False,
                unresolved=(
                    "Illuminate scenario requires an equipped Dawn's Wrath class line",
                ),
            )

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=base_state,
                minor_sorcery_active=False,
                unresolved=("Illuminate passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=base_state,
                minor_sorcery_active=False,
                unresolved=(
                    "Passive rank is not recorded for character: Illuminate",
                ),
            )
        if rank == 0:
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=base_state,
                minor_sorcery_active=False,
                unresolved=(),
            )

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=base_state,
                minor_sorcery_active=False,
                unresolved=(
                    "Passive max rank is not available in canonical data: Illuminate",
                ),
            )
        if rank < 0 or rank > maximum:
            return ExtremeTemplarIlluminateCombatStateResult(
                combat_state=base_state,
                minor_sorcery_active=False,
                unresolved=(
                    f"Invalid passive rank for Illuminate: {rank}/{maximum}",
                ),
            )

        return ExtremeTemplarIlluminateCombatStateResult(
            combat_state=CombatState(in_combat=True, active_buffs=("Minor Sorcery",)),
            minor_sorcery_active=True,
            unresolved=(),
        )