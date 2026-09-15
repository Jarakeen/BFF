from __future__ import annotations

"""Close the weapon-line passive challenger boundary for Extreme Weapon Damage.

The prior weapon/runtime audit established a reviewed Dual Wield dual-sword
Nirnhoned witness at 1064.4 sheet Weapon Damage delta and a Two-Handed
Nirnhoned pre-passive reference at 806.0. This audit reads canonical max-rank
weapon passive descriptions from eso.db and admits only effects whose wording
explicitly modifies Weapon/Spell Damage as a sheet stat. Damage-done, ability-
scoped, critical, penetration, sustain, movement, and other weapon mechanics do
not inflate the Weapon Damage record.
"""

import re
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATABASE = ROOT / "data" / "eso.db"
DUAL_SWORD_REVIEWED_DELTA = 1064.4
TWO_HANDED_NIRNHONED_PRE_PASSIVE = 806.0

WEAPON_LINES = (
    "Two Handed",
    "One Hand and Shield",
    "Dual Wield",
    "Bow",
    "Destruction Staff",
    "Restoration Staff",
)

_FLAT_POWER_PATTERNS = (
    re.compile(r"increases? your Weapon and Spell Damage by ([0-9]+(?:\.[0-9]+)?)", re.I),
    re.compile(r"adds? ([0-9]+(?:\.[0-9]+)?) Weapon and Spell Damage", re.I),
    re.compile(r"grants? ([0-9]+(?:\.[0-9]+)?) Weapon and Spell Damage", re.I),
)


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _clean(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split())


def _flat_sheet_power(description: str) -> float | None:
    text = _clean(description)
    for pattern in _FLAT_POWER_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def _weapon_passives() -> tuple[tuple[str, str, int, str], ...]:
    with sqlite3.connect(DATABASE) as db:
        skill_columns = _columns(db, "skill")
        rank_columns = _columns(db, "skill_rank")
        ability_columns = _columns(db, "ability")
        required_skill = {"id", "name", "is_passive"}
        required_rank = {"skill_id", "rank"}
        if not required_skill.issubset(skill_columns) or not required_rank.issubset(rank_columns):
            return ()

        line_expr = "COALESCE(NULLIF(TRIM(s.skill_line), ''), NULLIF(TRIM(a.skill_line), ''))" if "skill_line" in skill_columns and "skill_line" in ability_columns else (
            "TRIM(s.skill_line)" if "skill_line" in skill_columns else "TRIM(a.skill_line)"
        )
        description_parts: list[str] = []
        if "raw_description" in rank_columns:
            description_parts.append("NULLIF(TRIM(sr.raw_description), '')")
        if "description" in ability_columns:
            description_parts.append("NULLIF(TRIM(a.description), '')")
        if "description" in skill_columns:
            description_parts.append("NULLIF(TRIM(s.description), '')")
        description_expr = "COALESCE(" + ", ".join(description_parts + ["''"]) + ")"
        ability_join = "LEFT JOIN ability a ON a.id = sr.ability_id" if "ability_id" in rank_columns and "id" in ability_columns else "LEFT JOIN ability a ON 1=0"

        placeholders = ",".join("?" for _ in WEAPON_LINES)
        rows = db.execute(
            f"""
            WITH ranked AS (
                SELECT
                    s.id AS skill_id,
                    s.name AS passive_name,
                    {line_expr} AS skill_line,
                    sr.rank AS rank,
                    {description_expr} AS description,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.id
                        ORDER BY sr.rank DESC, sr.id DESC
                    ) AS rn
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                {ability_join}
                WHERE COALESCE(s.is_passive, 0) = 1
            )
            SELECT passive_name, skill_line, rank, description
            FROM ranked
            WHERE rn = 1
              AND skill_line IN ({placeholders})
            ORDER BY skill_line COLLATE NOCASE, passive_name COLLATE NOCASE
            """,
            WEAPON_LINES,
        ).fetchall()
    return tuple((str(name), str(line), int(rank), _clean(str(desc))) for name, line, rank, desc in rows)


def main() -> int:
    rows = _weapon_passives()
    unresolved: list[str] = []
    sheet_candidates: list[tuple[str, str, float, str]] = []
    reviewed_non_sheet: list[tuple[str, str, str]] = []

    for name, line, rank, description in rows:
        lower = description.casefold()
        mentions_power = "weapon and spell damage" in lower or "weapon damage" in lower
        flat = _flat_sheet_power(description)
        if flat is not None:
            sheet_candidates.append((name, line, flat, description))
            continue
        if mentions_power:
            scoped_markers = (
                "damage done",
                "with two handed",
                "with dual wield",
                "abilities",
                "attacks",
                "against",
                "critical damage",
                "offensive penetration",
            )
            if any(marker in lower for marker in scoped_markers):
                reviewed_non_sheet.append((name, line, description))
            else:
                unresolved.append(
                    f"{line} / {name}: mentions Weapon Damage but is not safely classified as flat sheet power: {description}"
                )

    best_two_handed = max(
        (row for row in sheet_candidates if row[1].casefold() == "two handed"),
        key=lambda row: row[2],
        default=None,
    )
    two_handed_total = TWO_HANDED_NIRNHONED_PRE_PASSIVE + (0.0 if best_two_handed is None else best_two_handed[2])
    dual_margin = DUAL_SWORD_REVIEWED_DELTA - two_handed_total
    dual_beats_two_handed = dual_margin >= -1e-9

    print("EXTREME WEAPON DAMAGE WEAPON PASSIVE CHALLENGERS")
    print(f"database={DATABASE}")
    print(f"weapon_passive_count={len(rows)}")
    print()
    print("SHEET-POWER PASSIVE CANDIDATES")
    for name, line, flat, description in sheet_candidates:
        print(f"  line={line!r} passive={name!r} flat={flat:.3f}")
        print(f"    description={description!r}")
    print(f"sheet_power_candidate_count={len(sheet_candidates)}")
    print()
    print("REVIEWED NON-SHEET POWER MENTIONS")
    for name, line, description in reviewed_non_sheet:
        print(f"  line={line!r} passive={name!r} description={description!r}")
    print(f"reviewed_non_sheet_count={len(reviewed_non_sheet)}")
    print()
    print("FINALIST COMPARISON")
    print(f"dual_sword_reviewed_delta={DUAL_SWORD_REVIEWED_DELTA:.3f}")
    print(f"two_handed_nirnhoned_pre_passive={TWO_HANDED_NIRNHONED_PRE_PASSIVE:.3f}")
    print(f"two_handed_best_sheet_passive={None if best_two_handed is None else best_two_handed[0]!r}")
    print(f"two_handed_best_sheet_passive_delta={0.0 if best_two_handed is None else best_two_handed[2]:.3f}")
    print(f"two_handed_finalist_delta={two_handed_total:.3f}")
    print(f"dual_wield_margin_over_two_handed={dual_margin:.3f}")
    print(f"dual_wield_beats_two_handed_sheet_power={dual_beats_two_handed}")
    print()
    print("PROOF GATES")
    print(f"weapon_passive_denominator_present={bool(rows)}")
    print(f"weapon_power_mentions_classified={not unresolved}")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved: {row}")
    closed = bool(rows) and not unresolved and dual_beats_two_handed
    print(f"weapon_damage_weapon_passive_frontier_closed={closed}")
    print("NEXT_STEP=combine the winning Dual Wield realization with named gear and class/runtime sheet-power challengers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
