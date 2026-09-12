from __future__ import annotations

"""Max-rank racial progression for hypothetical Extreme build candidates.

Extreme structural search is not constrained to the saved character's race.  When
it evaluates a hypothetical race, the selected race's canonical racial passive
ranks must travel with that race.  This service changes progression evidence only;
all racial stat math remains owned by ``RacialPassiveStatRepository`` and the
canonical Phase 5 calculation context.
"""

from dataclasses import replace
from pathlib import Path

from minmax.character_progression import CharacterProgression
from services.extreme_skill_universe_service import (
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


_RACE_SKILL_LINE_ALIASES = {
    "altmer": "high elf",
    "bosmer": "wood elf",
    "dunmer": "dark elf",
}


class ExtremeHypotheticalRacialProgressionService:
    """Install canonical max-rank passives for one hypothetical race."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        universe_service: ExtremeSkillUniverseService | None = None,
    ) -> None:
        if universe_service is None and database_path is None:
            raise ValueError("database_path is required when no skill universe service is supplied")
        self.universe_service = universe_service or ExtremeSkillUniverseService(database_path)  # type: ignore[arg-type]

    @staticmethod
    def _canonical_skill_line_race(race_name: str) -> str:
        race = " ".join(str(race_name or "").strip().split())
        key = race.casefold()
        return _RACE_SKILL_LINE_ALIASES.get(key, race)

    def normalize(
        self,
        progression: CharacterProgression,
        race_name: str,
    ) -> CharacterProgression:
        race = " ".join(str(race_name or "").strip().split())
        if not race:
            raise ValueError("hypothetical Extreme racial progression requires a race")

        racial = tuple(
            row
            for row in self.universe_service.passives()
            if row.domain is ExtremeSkillDomain.RACIAL
        )
        if not racial:
            raise ValueError("canonical racial passive inventory is unavailable")

        skill_line_race = self._canonical_skill_line_race(race)
        expected_line = f"{skill_line_race} Skills".casefold()
        selected = tuple(
            row
            for row in racial
            if str(row.skill_line or "").strip().casefold() == expected_line
        )
        if not selected:
            raise ValueError(f"canonical racial passives not found for hypothetical race: {race}")

        all_racial_names = {row.name.casefold() for row in racial if str(row.name or "").strip()}
        all_racial_lines = {
            str(row.skill_line or "").strip().casefold()
            for row in racial
            if str(row.skill_line or "").strip()
        }

        passive_ranks = {
            name: rank
            for name, rank in dict(progression.passive_ranks or {}).items()
            if str(name).casefold() not in all_racial_names
        }
        for row in selected:
            try:
                rank = int(row.max_rank or 0)
            except (TypeError, ValueError):
                rank = 0
            if rank <= 0:
                raise ValueError(
                    f"canonical max rank unavailable for racial passive: {row.name} [{row.skill_line}]"
                )
            passive_ranks[row.name] = rank

        inherited_lines = tuple(
            line
            for line in progression.owned_skill_lines
            if str(line or "").strip().casefold() not in all_racial_lines
        )
        selected_line = str(selected[0].skill_line or "").strip()
        owned_lines = tuple(dict.fromkeys((*inherited_lines, selected_line)))

        return replace(
            progression,
            owned_skill_lines=owned_lines,
            passive_ranks=passive_ranks,
        )
