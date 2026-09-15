from __future__ import annotations

"""Classify and compare U50 weapon-line Weapon Damage passive challengers.

The prior weapon/runtime audit now establishes the corrected Dual Wield
Nirnhoned dual-sword witness before Ambidextrous at 934.4 sheet Weapon Damage
delta and the Two-Handed Nirnhoned pre-passive reference at 806.0.

This audit reads canonical max-rank weapon passive descriptions from eso.db and
keeps distinct mechanic buckets distinct:

* conditional flat sheet power (Twin Blade and Blunt / Heavy Weapons swords),
* derived flat sheet power (Ambidextrous: % of off-hand weapon damage), and
* global percentage sheet power (Sword and Board).

Damage-done, ability-scoped, critical, penetration, sustain, movement, and other
weapon mechanics do not inflate the Weapon Damage sheet-stat record.
"""

from math import floor
import re
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.item_base_stats import (
    DUAL_WIELD_OFFHAND_POWER_RATIO,
    NAKED_LEVEL_50_POWER,
    WEAPON_NIRNHONED_PERCENT_GOLD,
    WEAPON_POWER_CP160_GOLD,
)

DATABASE = ROOT / "data" / "eso.db"

WEAPON_LINES = (
    "Two Handed",
    "One Hand and Shield",
    "Dual Wield",
    "Bow",
    "Destruction Staff",
    "Restoration Staff",
)

_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_NUMBER = r"([0-9]+(?:\.[0-9]+)?)"


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _clean(text: str) -> str:
    value = _COLOR.sub("", str(text or "")).replace("\n", " ")
    # Some imported U50 tooltips contain missing whitespace such as
    # "Increasesyour" or "Penetrationby". Repair only the known lexical joins
    # needed for semantic matching; the canonical numeric content is unchanged.
    value = value.replace("Increasesyour", "Increases your")
    value = value.replace("increasesyour", "increases your")
    value = value.replace("Penetrationby", "Penetration by")
    value = value.replace("increasesyour", "increases your")
    return " ".join(value.split())


def _weapon_passives() -> tuple[tuple[str, str, int, str], ...]:
    with sqlite3.connect(DATABASE) as db:
        skill_columns = _columns(db, "skill")
        rank_columns = _columns(db, "skill_rank")
        ability_columns = _columns(db, "ability")
        required_skill = {"id", "name", "is_passive"}
        required_rank = {"skill_id", "rank"}
        if not required_skill.issubset(skill_columns) or not required_rank.issubset(rank_columns):
            return ()

        line_expr = (
            "COALESCE(NULLIF(TRIM(s.skill_line), ''), NULLIF(TRIM(a.skill_line), ''))"
            if "skill_line" in skill_columns and "skill_line" in ability_columns
            else ("TRIM(s.skill_line)" if "skill_line" in skill_columns else "TRIM(a.skill_line)")
        )
        description_parts: list[str] = []
        if "raw_description" in rank_columns:
            description_parts.append("NULLIF(TRIM(sr.raw_description), '')")
        if "description" in ability_columns:
            description_parts.append("NULLIF(TRIM(a.description), '')")
        if "description" in skill_columns:
            description_parts.append("NULLIF(TRIM(s.description), '')")
        description_expr = "COALESCE(" + ", ".join(description_parts + ["''"]) + ")"
        ability_join = (
            "LEFT JOIN ability a ON a.id = sr.ability_id"
            if "ability_id" in rank_columns and "id" in ability_columns
            else "LEFT JOIN ability a ON 1=0"
        )

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
    return tuple(
        (str(name), str(line), int(rank), _clean(str(desc)))
        for name, line, rank, desc in rows
    )


def _passive_by_name(
    rows: tuple[tuple[str, str, int, str], ...],
    name: str,
) -> tuple[str, str, int, str] | None:
    key = name.strip().casefold()
    return next((row for row in rows if row[0].strip().casefold() == key), None)


def _extract(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, flags=re.I)
    return None if match is None else float(match.group(1))


def _nirn_bonus(power: float, *, scale: float = 1.0) -> float:
    improved = float(floor(float(power) * (1.0 + WEAPON_NIRNHONED_PERCENT_GOLD)))
    return (improved - float(power)) * float(scale)


def main() -> int:
    rows = _weapon_passives()
    unresolved: list[str] = []

    twin = _passive_by_name(rows, "Twin Blade and Blunt")
    heavy = _passive_by_name(rows, "Heavy Weapons")
    ambidextrous = _passive_by_name(rows, "Ambidextrous")
    sword_board = _passive_by_name(rows, "Sword and Board")

    for passive_name, row in (
        ("Twin Blade and Blunt", twin),
        ("Heavy Weapons", heavy),
        ("Ambidextrous", ambidextrous),
        ("Sword and Board", sword_board),
    ):
        if row is None:
            unresolved.append(f"canonical max-rank passive missing: {passive_name}")

    twin_per_sword = None if twin is None else _extract(
        rf"Each sword increases your Weapon and Spell Damage by {_NUMBER}",
        twin[3],
    )
    heavy_sword = None if heavy is None else _extract(
        rf"Swords increase your Weapon and Spell Damage by {_NUMBER}",
        heavy[3],
    )
    ambidextrous_percent = None if ambidextrous is None else _extract(
        rf"Increases Weapon and Spell Damage by {_NUMBER}% of off-hand weapon's damage",
        ambidextrous[3],
    )
    sword_board_percent = None if sword_board is None else _extract(
        rf"Increases your Weapon and Spell Damage by {_NUMBER}%",
        sword_board[3],
    )

    for label, value in (
        ("Twin Blade and Blunt sword magnitude", twin_per_sword),
        ("Heavy Weapons sword magnitude", heavy_sword),
        ("Ambidextrous off-hand percentage", ambidextrous_percent),
        ("Sword and Board global percentage", sword_board_percent),
    ):
        if value is None:
            unresolved.append(f"could not parse {label}")

    one_hand = float(WEAPON_POWER_CP160_GOLD["Sword"])
    two_hand = float(WEAPON_POWER_CP160_GOLD["Two-Handed"])

    dual_base = (one_hand - NAKED_LEVEL_50_POWER) + floor(
        one_hand * DUAL_WIELD_OFFHAND_POWER_RATIO
    )
    dual_nirn = _nirn_bonus(one_hand) + _nirn_bonus(
        one_hand,
        scale=DUAL_WIELD_OFFHAND_POWER_RATIO,
    )
    twin_total = 0.0 if twin_per_sword is None else 2.0 * twin_per_sword
    ambidextrous_flat = (
        0.0
        if ambidextrous_percent is None
        else one_hand * ambidextrous_percent / 100.0
    )
    dual_total = dual_base + dual_nirn + twin_total + ambidextrous_flat

    two_hand_base = two_hand - NAKED_LEVEL_50_POWER
    two_hand_nirn = _nirn_bonus(two_hand)
    two_hand_total = two_hand_base + two_hand_nirn + (heavy_sword or 0.0)

    sword_board_base = one_hand - NAKED_LEVEL_50_POWER
    sword_board_nirn = _nirn_bonus(one_hand)
    sword_board_local_flat = sword_board_base + sword_board_nirn
    sword_board_pct = 0.0 if sword_board_percent is None else sword_board_percent / 100.0

    dual_margin_over_two_hand = dual_total - two_hand_total
    dual_beats_two_hand = dual_margin_over_two_hand >= -1e-9

    # Sword and Board's +3% is a global additive sheet-power percentage, not a
    # local weapon flat. The most favorable possible comparison for Sword and
    # Board sets all common percentage bonuses to zero. If B is the pre-weapon,
    # pre-percent flat sheet value, Sword and Board can beat Dual Wield only if:
    #   (B + S&B_flat) * (1 + s&b_pct) > B + DW_flat
    # Any common positive percentage bonuses increase this threshold further.
    if sword_board_pct > 0.0:
        sword_board_minimum_baseline_to_beat_dual = (
            (dual_total - sword_board_local_flat) / sword_board_pct
            - sword_board_local_flat
        )
    else:
        sword_board_minimum_baseline_to_beat_dual = float("inf")

    reviewed_non_sheet: list[tuple[str, str, str]] = []
    relevant_names = {
        "twin blade and blunt",
        "heavy weapons",
        "ambidextrous",
        "sword and board",
    }
    for name, line, _rank, description in rows:
        lower = description.casefold()
        mentions_power = "weapon and spell damage" in lower or "weapon damage" in lower
        if not mentions_power or name.casefold() in relevant_names:
            continue
        scoped_markers = (
            "damage done",
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
                f"{line} / {name}: Weapon Damage mention remains unclassified: {description}"
            )

    print("EXTREME WEAPON DAMAGE WEAPON PASSIVE CHALLENGERS")
    print(f"database={DATABASE}")
    print(f"weapon_passive_count={len(rows)}")
    print()
    print("CANONICAL SHEET-POWER PASSIVES")
    print(f"twin_blade_sword_per_sword={0.0 if twin_per_sword is None else twin_per_sword:.3f}")
    print(f"heavy_weapons_two_handed_sword={0.0 if heavy_sword is None else heavy_sword:.3f}")
    print(f"ambidextrous_offhand_percent={0.0 if ambidextrous_percent is None else ambidextrous_percent:.3f}")
    print(f"sword_and_board_global_percent={0.0 if sword_board_percent is None else sword_board_percent:.3f}")
    print()
    print("DUAL WIELD")
    print(f"dual_base_delta={dual_base:.3f}")
    print(f"dual_nirnhoned_delta={dual_nirn:.3f}")
    print(f"twin_blade_two_swords_delta={twin_total:.3f}")
    print(f"ambidextrous_derived_flat_delta={ambidextrous_flat:.3f}")
    print(f"dual_wield_finalist_delta={dual_total:.3f}")
    print()
    print("TWO HANDED")
    print(f"two_handed_base_delta={two_hand_base:.3f}")
    print(f"two_handed_nirnhoned_delta={two_hand_nirn:.3f}")
    print(f"heavy_weapons_sword_delta={0.0 if heavy_sword is None else heavy_sword:.3f}")
    print(f"two_handed_finalist_delta={two_hand_total:.3f}")
    print(f"dual_wield_margin_over_two_handed={dual_margin_over_two_hand:.3f}")
    print(f"dual_wield_beats_two_handed_sheet_power={dual_beats_two_hand}")
    print()
    print("ONE HAND AND SHIELD THRESHOLD")
    print(f"sword_board_local_flat_delta={sword_board_local_flat:.3f}")
    print(f"sword_board_global_percent={0.0 if sword_board_percent is None else sword_board_percent:.3f}")
    print(
        "sword_board_minimum_preweapon_flat_baseline_to_beat_dual="
        f"{sword_board_minimum_baseline_to_beat_dual:.3f}"
    )
    print("sword_board_threshold_is_conservative_common_percent_zero=True")
    print("sword_board_requires_whole_build_upper_bound=True")
    print()
    print("REVIEWED NON-SHEET POWER MENTIONS")
    for name, line, description in reviewed_non_sheet:
        print(f"  line={line!r} passive={name!r} description={description!r}")
    print(f"reviewed_non_sheet_count={len(reviewed_non_sheet)}")
    print()
    print("PROOF GATES")
    print(f"weapon_passive_denominator_present={bool(rows)}")
    print(f"weapon_power_mentions_classified={not unresolved}")
    print(f"corrected_twin_blade_value_used={twin_per_sword == 64.0}")
    print(f"heavy_weapons_value_resolved={heavy_sword == 129.0}")
    print(f"ambidextrous_value_resolved={ambidextrous_percent == 3.0}")
    print(f"sword_board_percent_resolved={sword_board_percent == 3.0}")
    print(f"dual_wield_beats_two_handed={dual_beats_two_hand}")
    print("sword_board_global_percent_challenger_preserved=True")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved: {row}")

    classification_closed = bool(rows) and not unresolved and dual_beats_two_hand
    print(f"weapon_damage_weapon_passive_classification_closed={classification_closed}")
    print("weapon_damage_weapon_passive_frontier_closed=False")
    print(
        "NEXT_STEP=carry the conservative Sword and Board threshold into whole-build "
        "named-gear/class/runtime composition; if the whole-build pre-weapon flat upper "
        "bound stays below the printed threshold, Dual Wield becomes the proven weapon champion"
    )
    return 0 if classification_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
