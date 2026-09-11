from __future__ import annotations

"""Proof-reduced active-bar witnesses for Extreme max-resource objectives.

This service owns no ESO stat arithmetic.  It inventories canonical active skills
and builds the smallest legal bar witnesses needed by the reviewed resource
passives:

* Dark Vigor: maximize distinct Shadow abilities on the active bar.
* Magicka Flood: one Siphoning ability is sufficient.
* Magicka Controller: maximize distinct Mages Guild abilities, jointly with the
  one-slot Magicka Flood trigger when Siphoning is available.

Class-line legality comes from the already-validated Extreme class route so legal
subclass lines are not rejected merely because they differ from the base class.
Normal slots (0-4) and the Ultimate slot (5) remain distinct, and duplicate active
skill families are never used twice on one witness bar.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.guild_passive_input_resolver import GuildPassiveInputResolver
from minmax.nightblade_passive_input_resolver import NightbladePassiveInputResolver
from minmax.passive_math import mages_guild_magicka_controller_percent
from models.build_model import BAR_SKILL_COUNT, PlayerBuild
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    canonical_class_skill_line_id,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillUniverseService,
)


@dataclass(frozen=True)
class ExtremeResourceActiveBarState:
    objective_key: str
    skills: tuple[str, ...]
    shadow_slots: int = 0
    siphoning_slots: int = 0
    mages_guild_slots: int = 0
    reviewed_percent_bonus: float = 0.0

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.objective_key,
            self.skills,
            self.shadow_slots,
            self.siphoning_slots,
            self.mages_guild_slots,
        )


@dataclass(frozen=True)
class ExtremeResourceActiveBarStateCatalog:
    objective_key: str
    states: tuple[ExtremeResourceActiveBarState, ...]
    active_skills_reviewed: int
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()


class ExtremeResourceActiveBarStateService:
    """Build proof-reduced active-bar witnesses for reviewed resource passives."""

    SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
    SHADOW = NightbladePassiveInputResolver.SHADOW_ID
    SIPHONING = NightbladePassiveInputResolver.SIPHONING_ID
    MAGES_GUILD = GuildPassiveInputResolver.MAGES_GUILD

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_universe_service: ExtremeSkillUniverseService | None = None,
    ) -> None:
        if database_path is None and skill_universe_service is None:
            raise ValueError("database_path or skill_universe_service is required")
        self.database_path = Path(database_path) if database_path is not None else None
        self.skill_universe_service = skill_universe_service or ExtremeSkillUniverseService(
            self.database_path  # type: ignore[arg-type]
        )

    @staticmethod
    def _line_key(value: object) -> str:
        return canonical_class_skill_line_id(value)

    @staticmethod
    def _family_key(row: ExtremePlayerSkillRecord) -> tuple[int, str]:
        return (
            int(row.base_ability_id or row.skill_id),
            row.skill_line.casefold(),
        )

    @staticmethod
    def _is_ultimate(row: ExtremePlayerSkillRecord) -> bool:
        return "ultimate" in str(row.skill_type or "").casefold()

    @classmethod
    def _distinct_rows(
        cls,
        rows: tuple[ExtremePlayerSkillRecord, ...],
        *,
        ultimate: bool,
    ) -> tuple[ExtremePlayerSkillRecord, ...]:
        selected: dict[tuple[int, str], ExtremePlayerSkillRecord] = {}
        for row in rows:
            if cls._is_ultimate(row) is not ultimate:
                continue
            key = cls._family_key(row)
            current = selected.get(key)
            if current is None or (row.name.casefold(), row.skill_id) < (
                current.name.casefold(),
                current.skill_id,
            ):
                selected[key] = row
        return tuple(
            sorted(
                selected.values(),
                key=lambda row: (row.name.casefold(), row.skill_id),
            )
        )

    @classmethod
    def _line_rows(
        cls,
        actives: tuple[ExtremePlayerSkillRecord, ...],
        line_id: str,
    ) -> tuple[ExtremePlayerSkillRecord, ...]:
        return tuple(
            row
            for row in actives
            if cls._line_key(row.skill_line) == cls._line_key(line_id)
            and row.max_rank_ability_id is not None
            and not row.is_crafted
        )

    @staticmethod
    def _bar_from_rows(
        normal_rows: tuple[ExtremePlayerSkillRecord, ...] = (),
        ultimate_row: ExtremePlayerSkillRecord | None = None,
    ) -> tuple[str, ...]:
        bar = [""] * (BAR_SKILL_COUNT + 1)
        for index, row in enumerate(normal_rows[:BAR_SKILL_COUNT]):
            bar[index] = row.name
        if ultimate_row is not None:
            bar[BAR_SKILL_COUNT] = ultimate_row.name
        return tuple(bar)

    @staticmethod
    def _route_lines(route: ExtremeHealClassRoute) -> frozenset[str]:
        return frozenset(canonical_class_skill_line_id(line) for line in route.equipped_skill_lines)

    @classmethod
    def _empty_state(cls, key: str) -> ExtremeResourceActiveBarState:
        return ExtremeResourceActiveBarState(
            objective_key=key,
            skills=tuple("" for _ in range(BAR_SKILL_COUNT + 1)),
        )

    def build(
        self,
        objective_key: str,
        route: ExtremeHealClassRoute,
    ) -> ExtremeResourceActiveBarStateCatalog:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource active-bar objective: {objective_key!r}")

        actives = tuple(self.skill_universe_service.actives())
        if not actives:
            return ExtremeResourceActiveBarStateCatalog(
                objective_key=key,
                states=(self._empty_state(key),),
                active_skills_reviewed=0,
                denominator_proven=False,
                unresolved=("Canonical active-skill universe is empty for Extreme resource bar search",),
            )

        route_lines = self._route_lines(route)
        shadow_rows = self._line_rows(actives, self.SHADOW) if self.SHADOW in route_lines else ()
        siphoning_rows = self._line_rows(actives, self.SIPHONING) if self.SIPHONING in route_lines else ()
        mages_rows = self._line_rows(actives, self.MAGES_GUILD)

        shadow_normal = self._distinct_rows(shadow_rows, ultimate=False)
        shadow_ultimate = self._distinct_rows(shadow_rows, ultimate=True)
        siphoning_normal = self._distinct_rows(siphoning_rows, ultimate=False)
        siphoning_ultimate = self._distinct_rows(siphoning_rows, ultimate=True)
        mages_normal = self._distinct_rows(mages_rows, ultimate=False)
        mages_ultimate = self._distinct_rows(mages_rows, ultimate=True)

        state = self._empty_state(key)
        unresolved: list[str] = []

        if key == "max_health" and self.SHADOW in route_lines:
            normals = shadow_normal[:BAR_SKILL_COUNT]
            ultimate = shadow_ultimate[0] if shadow_ultimate else None
            count = len(normals) + int(ultimate is not None)
            if count == 0:
                unresolved.append("No canonical bar-eligible Shadow active witness is available for Dark Vigor")
            else:
                state = ExtremeResourceActiveBarState(
                    objective_key=key,
                    skills=self._bar_from_rows(normals, ultimate),
                    shadow_slots=count,
                    reviewed_percent_bonus=(
                        NightbladePassiveInputResolver.DARK_VIGOR_HEALTH_PERCENT_PER_SHADOW_SLOT
                        * count
                    ),
                )

        elif key == "max_stamina" and self.SIPHONING in route_lines:
            if siphoning_normal:
                state = ExtremeResourceActiveBarState(
                    objective_key=key,
                    skills=self._bar_from_rows((siphoning_normal[0],)),
                    siphoning_slots=1,
                    reviewed_percent_bonus=NightbladePassiveInputResolver.MAGICKA_FLOOD_PERCENT,
                )
            elif siphoning_ultimate:
                state = ExtremeResourceActiveBarState(
                    objective_key=key,
                    skills=self._bar_from_rows((), siphoning_ultimate[0]),
                    siphoning_slots=1,
                    reviewed_percent_bonus=NightbladePassiveInputResolver.MAGICKA_FLOOD_PERCENT,
                )
            else:
                unresolved.append("No canonical bar-eligible Siphoning active witness is available for Magicka Flood")

        elif key == "max_magicka":
            candidates: list[ExtremeResourceActiveBarState] = []

            # Mages-only candidate.  Every Mages Guild slot is positive for
            # Magicka Controller, so all distinct legal slots are filled.
            m_normals = mages_normal[:BAR_SKILL_COUNT]
            m_ultimate = mages_ultimate[0] if mages_ultimate else None
            m_count = len(m_normals) + int(m_ultimate is not None)
            candidates.append(
                ExtremeResourceActiveBarState(
                    objective_key=key,
                    skills=self._bar_from_rows(m_normals, m_ultimate),
                    mages_guild_slots=m_count,
                    reviewed_percent_bonus=mages_guild_magicka_controller_percent(m_count),
                )
            )

            if self.SIPHONING in route_lines:
                # One Siphoning slot is sufficient for Magicka Flood. Additional
                # Siphoning slots are dominated because they replace a positive
                # Magicka Controller slot without increasing Flood's 6% trigger.
                if siphoning_normal:
                    remaining_mages = mages_normal[: BAR_SKILL_COUNT - 1]
                    ult = mages_ultimate[0] if mages_ultimate else None
                    m_count = len(remaining_mages) + int(ult is not None)
                    candidates.append(
                        ExtremeResourceActiveBarState(
                            objective_key=key,
                            skills=self._bar_from_rows((siphoning_normal[0], *remaining_mages), ult),
                            siphoning_slots=1,
                            mages_guild_slots=m_count,
                            reviewed_percent_bonus=(
                                NightbladePassiveInputResolver.MAGICKA_FLOOD_PERCENT
                                + mages_guild_magicka_controller_percent(m_count)
                            ),
                        )
                    )
                if siphoning_ultimate:
                    remaining_mages = mages_normal[:BAR_SKILL_COUNT]
                    m_count = len(remaining_mages)
                    candidates.append(
                        ExtremeResourceActiveBarState(
                            objective_key=key,
                            skills=self._bar_from_rows(remaining_mages, siphoning_ultimate[0]),
                            siphoning_slots=1,
                            mages_guild_slots=m_count,
                            reviewed_percent_bonus=(
                                NightbladePassiveInputResolver.MAGICKA_FLOOD_PERCENT
                                + mages_guild_magicka_controller_percent(m_count)
                            ),
                        )
                    )
                if not siphoning_normal and not siphoning_ultimate:
                    unresolved.append("No canonical bar-eligible Siphoning active witness is available for Magicka Flood")

            state = max(
                candidates,
                key=lambda row: (row.reviewed_percent_bonus, row.skills),
            )

        return ExtremeResourceActiveBarStateCatalog(
            objective_key=key,
            states=(state,),
            active_skills_reviewed=len(actives),
            denominator_proven=not unresolved,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeResourceActiveBarState,
        *,
        active_bar: str,
    ) -> PlayerBuild:
        result = PlayerBuild.from_dict(build.to_dict())
        skills = list(state.skills)
        if str(active_bar or "front").strip().casefold() == "back":
            result.BackBarSkills = skills
        else:
            result.FrontBarSkills = skills
        return result
