from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3


@dataclass(frozen=True)
class RotationHealerEsoLogsCanonicalSkillAliases:
    canonical_skill_id: str
    ability_game_ids: tuple[int, ...]
    evidence: tuple[str, ...]

    def contains(self, ability_game_id: int | None) -> bool:
        return ability_game_id is not None and int(ability_game_id) in self.ability_game_ids


@dataclass(frozen=True)
class RotationHealerEsoLogsReviewedPeriodicEffectAliases:
    canonical_skill_id: str
    coefficient_number: int
    ability_game_ids: tuple[int, ...]
    evidence: tuple[str, ...]
    game_version: str

    def contains(self, ability_game_id: int | None) -> bool:
        return ability_game_id is not None and int(ability_game_id) in self.ability_game_ids


def _canonical_skill_id(value: object) -> str:
    """Normalize imported/display skill names to canonical lower-snake-case ids."""

    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


# Reviewed observational mappings from ESO Logs report FPy6Tc9BzwQNbfVK,
# Lokkestiiz fights 6, 27, and 41, caster sourceID 7. These numeric IDs are
# periodic healing-event aliases only. They do not redefine canonical skill
# identity and are deliberately component-specific where the skill has more
# than one healing component.
_REVIEWED_PERIODIC_EFFECT_ALIASES: dict[tuple[str, int], tuple[int, ...]] = {
    ("budding_seeds", 2): (129434,),
    ("radiating_regeneration", 1): (40079,),
    ("illustrious_healing", 1): (40059,),
    ("energy_orb", 1): (42039,),
    ("echoing_vigor", 1): (61506,),
}

_REVIEWED_PERIODIC_EFFECT_EVIDENCE: dict[tuple[str, int], tuple[str, ...]] = {
    ("budding_seeds", 2): (
        "ESO Logs FPy6Tc9BzwQNbfVK fights 6/27/41 caster sourceID 7",
        "abilityID 129434 appeared as tick healing in 50/50 Budding Seeds cast windows across 3/3 fights (1270 events)",
        "reviewed as Budding Seeds coefficient 2 periodic field-heal evidence; abilityID 85841 remains unpromoted",
    ),
    ("radiating_regeneration", 1): (
        "ESO Logs FPy6Tc9BzwQNbfVK fights 6/27/41 caster sourceID 7",
        "abilityID 40079 appeared as tick healing in 29/29 Radiating Regeneration cast windows across 3/3 fights (468 events)",
        "same observed numeric ID is used for the cast and periodic healing stream in this corpus",
    ),
    ("illustrious_healing", 1): (
        "ESO Logs FPy6Tc9BzwQNbfVK fights 6/27/41 caster sourceID 7",
        "abilityID 40059 appeared as tick healing in 79/79 Illustrious Healing cast windows across 3/3 fights (2632 events)",
    ),
    ("energy_orb", 1): (
        "ESO Logs FPy6Tc9BzwQNbfVK fights 6/27/41 caster sourceID 7",
        "abilityID 42039 appeared as tick healing in 25/25 Energy Orb cast windows across 3/3 fights (785 events)",
    ),
    ("echoing_vigor", 1): (
        "ESO Logs FPy6Tc9BzwQNbfVK fights 6/27/41 caster sourceID 7",
        "abilityID 61506 appeared as tick healing in 53/53 Echoing Vigor cast windows across 3/3 fights (1913 events)",
    ),
}


class RotationHealerEsoLogsCanonicalSkillAliasService:
    """Resolve ESO Logs numeric aliases outward from canonical skill identity.

    Canonical identity is the persisted lower-snake-case string id (for example
    ``radiating_regeneration``). Numeric ability ids are evidence aliases only;
    they never determine semantic identity by themselves.

    Imported ``ability.index_name`` values may use display-style whitespace and
    punctuation. They are normalized to the same semantic lower-snake-case form
    before comparison rather than requiring their storage representation to match
    canonical ids byte-for-byte.

    Reviewed periodic healing-effect aliases are kept separate from canonical cast
    aliases. That separation matters for skills such as Budding Seeds, where cast,
    periodic field healing, delayed bloom, and synergy events can use different
    numeric IDs while still belonging to one semantic skill family.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def resolve(self, canonical_skill_id: str) -> RotationHealerEsoLogsCanonicalSkillAliases | None:
        key = _canonical_skill_id(canonical_skill_id)
        if not key or not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "ability" not in tables:
                return None

            ability_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(ability)").fetchall()
            }
            if not {"ability_id", "index_name"}.issubset(ability_columns):
                return None

            rows = connection.execute(
                """
                SELECT DISTINCT ability_id, index_name
                FROM ability
                WHERE ability_id IS NOT NULL
                  AND TRIM(COALESCE(index_name, '')) <> ''
                ORDER BY ability_id
                """
            ).fetchall()
            ids = tuple(
                int(row["ability_id"])
                for row in rows
                if _canonical_skill_id(row["index_name"]) == key
            )
            if not ids:
                return None

            return RotationHealerEsoLogsCanonicalSkillAliases(
                canonical_skill_id=key,
                ability_game_ids=ids,
                evidence=(
                    f"canonical skill id {key}",
                    "numeric aliases resolved from semantically normalized ability.index_name",
                    "ability ids are observational aliases, not canonical identity",
                ),
            )

    def reviewed_periodic_effects(
        self,
        canonical_skill_id: str,
        *,
        coefficient_number: int,
        game_version: str = "U50",
    ) -> RotationHealerEsoLogsReviewedPeriodicEffectAliases | None:
        key = _canonical_skill_id(canonical_skill_id)
        component = (key, int(coefficient_number))
        aliases = _REVIEWED_PERIODIC_EFFECT_ALIASES.get(component)
        if not aliases:
            return None
        if str(game_version).strip().upper() != "U50":
            return None

        return RotationHealerEsoLogsReviewedPeriodicEffectAliases(
            canonical_skill_id=key,
            coefficient_number=int(coefficient_number),
            ability_game_ids=aliases,
            evidence=_REVIEWED_PERIODIC_EFFECT_EVIDENCE[component]
            + (
                "numeric effect IDs are reviewed observational aliases, not canonical identity",
            ),
            game_version="U50",
        )
