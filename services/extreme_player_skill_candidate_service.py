from __future__ import annotations

"""Route-aware active-skill candidate universe for Extreme Builds.

Unlike the original class-line-only materializer, this service admits every
canonical player active skill that a route could legally use: equipped class
lines, weapon lines supported by the current bar, guild/alliance/world combat
lines, transformed Vampire/Werewolf skills, and configured scribed skills.

It does not score tooltip prose.  Mechanical value remains owned by reviewed
active-effect services; this layer answers only whether a canonical skill is a
legal candidate for the requested build/bar context.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


@dataclass(frozen=True)
class ExtremePlayerSkillLegalityContext:
    equipped_class_lines: tuple[str, ...]
    equipped_weapon_lines: tuple[str, ...] = ()
    vampire: bool = False
    werewolf: bool = False
    transformed_form: str | None = None
    allowed_scribed_ability_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.vampire and self.werewolf:
            raise ValueError("A player route cannot be both Vampire and Werewolf")


class ExtremePlayerSkillCandidateService:
    """Filter the complete canonical active-skill universe by game legality."""

    def __init__(self, database_path: str | Path) -> None:
        self.universe = ExtremeSkillUniverseService(database_path)

    @staticmethod
    def _class_line_allowed(
        row: ExtremePlayerSkillRecord,
        context: ExtremePlayerSkillLegalityContext,
    ) -> bool:
        allowed = {_key(line) for line in context.equipped_class_lines}
        return row.line_key in allowed

    @staticmethod
    def _weapon_line_allowed(
        row: ExtremePlayerSkillRecord,
        context: ExtremePlayerSkillLegalityContext,
    ) -> bool:
        allowed = {_key(line) for line in context.equipped_weapon_lines}
        return row.line_key in allowed

    @staticmethod
    def _world_line_allowed(
        row: ExtremePlayerSkillRecord,
        context: ExtremePlayerSkillLegalityContext,
    ) -> bool:
        line = row.line_key
        form = _key(context.transformed_form)
        if line == "vampire":
            return context.vampire and form == "vampire"
        if line == "werewolf":
            return context.werewolf and form == "werewolf"
        return True

    @staticmethod
    def _scribed_allowed(
        row: ExtremePlayerSkillRecord,
        context: ExtremePlayerSkillLegalityContext,
    ) -> bool:
        if not row.is_crafted:
            return True
        return bool(
            row.max_rank_ability_id is not None
            and int(row.max_rank_ability_id) in set(context.allowed_scribed_ability_ids)
        )

    @classmethod
    def legal_for_context(
        cls,
        row: ExtremePlayerSkillRecord,
        context: ExtremePlayerSkillLegalityContext,
    ) -> bool:
        if row.is_passive or not row.is_player or row.max_rank_ability_id is None:
            return False
        if row.known_noncombat_line:
            return False
        if not cls._scribed_allowed(row, context):
            return False

        if row.domain is ExtremeSkillDomain.CLASS:
            return cls._class_line_allowed(row, context)
        if row.domain is ExtremeSkillDomain.WEAPON:
            return cls._weapon_line_allowed(row, context)
        if row.domain is ExtremeSkillDomain.WORLD:
            return cls._world_line_allowed(row, context)
        if row.domain in {
            ExtremeSkillDomain.ARMOR,
            ExtremeSkillDomain.GUILD,
            ExtremeSkillDomain.ALLIANCE_WAR,
            ExtremeSkillDomain.OTHER,
        }:
            return row.combat_line
        return False

    def candidates(
        self,
        context: ExtremePlayerSkillLegalityContext,
        *,
        ultimate: bool | None = None,
    ) -> tuple[ExtremePlayerSkillRecord, ...]:
        rows = tuple(
            row
            for row in self.universe.actives()
            if self.legal_for_context(row, context)
        )
        if ultimate is not None:
            want = bool(ultimate)
            rows = tuple(
                row
                for row in rows
                if ("ultimate" in row.skill_type.casefold()) is want
            )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.domain.value,
                    row.skill_line.casefold(),
                    row.name.casefold(),
                    row.max_rank_ability_id or 0,
                ),
            )
        )
