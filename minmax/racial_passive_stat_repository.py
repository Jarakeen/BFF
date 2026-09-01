from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .character_progression import CharacterProgression


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_NUMBER = r"([0-9]+(?:\.[0-9]+)?)"


@dataclass(frozen=True)
class RacialPassiveResolution:
    stats: dict[str, float]
    boundaries: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class RacialPassiveStatRepository:
    """Resolve purchased racial passive ranks from canonical ability tooltips.

    The historical ``race_stat`` table is aggregate/max-rank data. This
    repository instead reads the concrete ability row for the character's
    recorded passive rank, so Phase 5 never grants an unpurchased racial rank.
    """

    NONCOMBAT_PASSIVE_NAMES = frozenset({
        "opportunist",
    })

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _clean(text: object) -> str:
        value = _COLOR.sub("", str(text or ""))
        return " ".join(value.split())

    def _racial_passive_rows(self, race_name: str) -> tuple[sqlite3.Row, ...]:
        if not self.database_path.exists():
            return ()
        race = self._clean(race_name)
        if not race:
            return ()
        expected_line = f"{race} Skills".casefold()
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """
                SELECT
                    s.name AS passive_name,
                    sr.rank AS rank,
                    a.description AS description
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(s.is_passive, 0) = 1
                  AND COALESCE(s.is_player, 0) = 1
                  AND LOWER(TRIM(COALESCE(s.skill_line, ''))) = ?
                ORDER BY s.name COLLATE NOCASE, sr.rank
                """,
                (expected_line,),
            ).fetchall()
        return tuple(rows)

    @staticmethod
    def _add(stats: dict[str, float], key: str, value: float) -> None:
        stats[key] = stats.get(key, 0.0) + float(value)

    def _parse_description(
        self,
        passive_name: str,
        description: str,
    ) -> tuple[dict[str, float], list[str], list[str]]:
        clean = self._clean(description)
        stats: dict[str, float] = {}
        boundaries: list[str] = []
        unresolved: list[str] = []

        if passive_name.casefold() in self.NONCOMBAT_PASSIVE_NAMES:
            boundaries.append(f"Non-combat racial passive outside combat capability audit: {passive_name}")
            return stats, boundaries, unresolved

        patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
            (rf"Increases your Max Health by {_NUMBER}", ("max_health",)),
            (rf"Increases your Max Magicka by {_NUMBER}", ("max_magicka",)),
            (rf"Increases your Max Stamina by {_NUMBER}", ("max_stamina",)),
            (rf"Increases your Health Recovery by {_NUMBER}", ("health_recovery",)),
            (rf"Increases your Magicka Recovery by {_NUMBER}", ("magicka_recovery",)),
            (rf"Increases your Stamina Recovery by {_NUMBER}", ("stamina_recovery",)),
            (rf"Increases your Weapon and Spell Damage by {_NUMBER}", ("weapon_damage", "spell_damage")),
            (rf"Increases your Spell Damage by {_NUMBER}", ("spell_damage",)),
            (rf"Increases your Weapon Damage by {_NUMBER}", ("weapon_damage",)),
            (rf"Increases your Spell Resistance by {_NUMBER}", ("spell_resistance",)),
            (rf"Increases your Physical Resistance by {_NUMBER}", ("physical_resistance",)),
        )

        matched_any = False
        for pattern, keys in patterns:
            for match in re.finditer(pattern, clean, flags=re.IGNORECASE):
                matched_any = True
                amount = float(match.group(1))
                for key in keys:
                    self._add(stats, key, amount)

        lowered = clean.casefold()
        if "this effect is doubled if" in lowered:
            boundaries.append(
                f"Conditional racial passive bonus requires combat-state model: {passive_name}"
            )
        if "reduces the magicka cost" in lowered or "reduces the stamina cost" in lowered or "reduces the cost" in lowered:
            boundaries.append(
                f"Racial ability-cost reduction requires cost-stat model: {passive_name}"
            )
        if not matched_any and not boundaries:
            unresolved.append(
                f"Racial passive tooltip is not yet stat-mapped: {passive_name}"
            )
        return stats, boundaries, unresolved

    def resolve(
        self,
        race_name: str,
        progression: CharacterProgression,
    ) -> RacialPassiveResolution:
        if progression.passive_ranks is None:
            return RacialPassiveResolution(stats={})

        rows = self._racial_passive_rows(race_name)
        if not rows:
            race = self._clean(race_name)
            return RacialPassiveResolution(
                stats={},
                unresolved=(f"Canonical racial passive rows not found: {race}",) if race else (),
            )

        by_name_rank: dict[tuple[str, int], sqlite3.Row] = {}
        passive_names: dict[str, str] = {}
        for row in rows:
            name = self._clean(row["passive_name"])
            key = name.casefold()
            passive_names[key] = name
            by_name_rank[(key, int(row["rank"] or 0))] = row

        stats: dict[str, float] = {}
        boundaries: list[str] = []
        unresolved: list[str] = []
        for key, canonical_name in passive_names.items():
            rank = progression.passive_rank(canonical_name)
            if rank is None:
                unresolved.append(
                    f"Passive rank is not recorded for character: {canonical_name}"
                )
                continue
            if rank <= 0:
                continue
            row = by_name_rank.get((key, int(rank)))
            if row is None:
                unresolved.append(
                    f"Racial passive rank not found in canonical data: {canonical_name} {rank}"
                )
                continue
            parsed, passive_boundaries, passive_unresolved = self._parse_description(
                canonical_name,
                str(row["description"] or ""),
            )
            for stat, value in parsed.items():
                self._add(stats, stat, value)
            boundaries.extend(passive_boundaries)
            unresolved.extend(passive_unresolved)

        return RacialPassiveResolution(
            stats=stats,
            boundaries=tuple(dict.fromkeys(boundaries)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
