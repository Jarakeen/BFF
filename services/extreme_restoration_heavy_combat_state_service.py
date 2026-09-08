from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.weapon_type import WeaponSkillLine, WeaponType, resolve_weapon_skill_line
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.eso_weapon_type_id import weapon_type_from_saved_name
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeRestorationHeavyCombatStateResult:
    combat_state: CombatState
    major_mending_active: bool
    unresolved: tuple[str, ...]


class ExtremeRestorationHeavyCombatStateService:
    """Resolve the reviewed Essence Drain post-heavy-attack combat state.

    The caller must explicitly state that a fully charged Restoration Staff heavy
    attack has completed. This service never infers the trigger from a slotted
    weapon or passive alone. When the trigger, active weapon, owned skill line,
    and canonical max passive rank are all proven, the result contributes Major
    Mending through ``CombatState`` so the normal named-buff layer owns the +16%
    Healing Done semantics.

    Missing or partial passive evidence preserves the unbuffed state and returns
    an explicit blocker instead of assigning unknown mechanic value as zero.
    """

    PASSIVE_NAME = "Essence Drain"

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

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_bar: str = "front",
        fully_charged_heavy_attack_completed: bool = False,
    ) -> ExtremeRestorationHeavyCombatStateResult:
        if not fully_charged_heavy_attack_completed:
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=CombatState(),
                major_mending_active=False,
                unresolved=(),
            )

        base_state = CombatState(in_combat=True)
        if self._active_weapon_line(build, active_bar) is not WeaponSkillLine.RESTORATION_STAFF:
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                unresolved=(
                    "Essence Drain scenario requires an active Restoration Staff",
                ),
            )

        if not progression.owns_skill_line("Restoration Staff"):
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                unresolved=(
                    "Essence Drain scenario requires owned Restoration Staff progression",
                ),
            )

        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                unresolved=(
                    "Passive rank is not recorded for character: Essence Drain",
                ),
            )
        if rank == 0:
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                unresolved=(),
            )

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                unresolved=(
                    "Passive max rank is not available in canonical data: Essence Drain",
                ),
            )
        if rank != maximum:
            return ExtremeRestorationHeavyCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                unresolved=(
                    f"Partial passive rank is not yet modeled: Essence Drain {rank}/{maximum}",
                ),
            )

        return ExtremeRestorationHeavyCombatStateResult(
            combat_state=CombatState(in_combat=True, active_buffs=("Major Mending",)),
            major_mending_active=True,
            unresolved=(),
        )

    @staticmethod
    def _active_weapon_line(build: PlayerBuild, active_bar: str) -> WeaponSkillLine | None:
        main, offhand = build.active_weapon_slots(str(active_bar or "front").casefold())
        main_type = weapon_type_from_saved_name(main.WeaponType)
        offhand_type = weapon_type_from_saved_name(offhand.WeaponType)
        if main_type is None:
            return None
        if offhand_type is None:
            offhand_type = WeaponType.NONE
        try:
            return resolve_weapon_skill_line(main_type, offhand_type)
        except ValueError:
            return None
