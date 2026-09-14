from __future__ import annotations

"""Compare the corrected active-bar Recovery winner against a Minor Intellect carrier.

This targeted audit starts from the already-proven corrected five-normal-slot checkpoint
(1 Animal Companions + 4 Support) and asks whether replacing one Support skill with a
proven self-usable Minor Intellect carrier increases Magicka Recovery. It intentionally
reuses the canonical named-buff semantics and SkillEffectRepository rather than treating
a reference-table ability name as sufficient proof.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.named_combat_buffs import effects_for_buff
from minmax.skill_effect_repository import SkillEffectRepository
from minmax.stat_ids import StatId
from minmax.support_target_type import SupportTargetType
from tools.audit_extreme_magicka_recovery_combined_active_bar_frontier import (
    EXPECTED_ROUTE_IDS,
    _bar_shape_legal,
    _capacity,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService

OBJECTIVE = "magicka_recovery"
TARGET_BUFF = "Minor Intellect"
CARRIER_NAME = "Arcanist's Domain"
CARRIER_LINE = "curative_runeforms"
BASELINE_ANIMAL_SLOTS = 1
BASELINE_SUPPORT_SLOTS = 4
CHALLENGER_ANIMAL_SLOTS = 1
CHALLENGER_SUPPORT_SLOTS = 3
CHALLENGER_MINOR_INTELLECT_SLOTS = 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--pre-percent", type=float, default=5184.294)
    parser.add_argument("--baseline-percent", type=float, default=121.0)
    parser.add_argument("--common-major-intellect-percent", type=float, default=30.0)
    return parser


def _rank4_carrier(database: Path):
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            """
            SELECT ability_id, name, skill_line, rank, base_ability_id, morph
            FROM ability
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND rank = 4
            ORDER BY ability_id DESC
            LIMIT 1
            """,
            (CARRIER_NAME,),
        ).fetchone()
    return dict(row) if row is not None else None


def _minor_intellect_percent() -> tuple[float | None, tuple[str, ...]]:
    rows = tuple(
        row
        for row in effects_for_buff(TARGET_BUFF)
        if row.stat is StatId.MAGICKA_RECOVERY and row.bucket == "resource_percent"
    )
    if len(rows) != 1:
        return None, (f"Expected one canonical {TARGET_BUFF} Magicka Recovery effect, found {len(rows)}",)
    return float(rows[0].value) * 100.0, ()


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    unresolved: list[str] = []

    carrier = _rank4_carrier(database)
    if carrier is None:
        unresolved.append(f"Rank-4 carrier row missing: {CARRIER_NAME}")
        carrier_line = ""
        carrier_id = -1
    else:
        carrier_line = str(carrier["skill_line"] or "").strip().casefold().replace(" ", "_")
        carrier_id = int(carrier["ability_id"])

    percent, percent_unresolved = _minor_intellect_percent()
    unresolved.extend(percent_unresolved)
    minor_percent = float(percent or 0.0)

    repository = SkillEffectRepository(database)
    carrier_effects = tuple(
        effect
        for effect in (() if carrier_id < 0 else repository.resolve(carrier_id))
        if str(effect.name or "").strip().casefold().replace(" ", "_") == "minor_intellect"
    )
    self_usable = tuple(
        effect
        for effect in carrier_effects
        if effect.target_type is SupportTargetType.SELF
        and effect.duration is not None
        and float(effect.duration) > 0.0
        and effect.condition is None
        and effect.trigger is None
    )
    if not self_usable:
        unresolved.append(f"No proven self-usable Minor Intellect effect for {CARRIER_NAME}")

    route_contains_carrier_line = carrier_line == CARRIER_LINE and CARRIER_LINE in EXPECTED_ROUTE_IDS
    if not route_contains_carrier_line:
        unresolved.append(
            f"Carrier line {carrier_line!r} is not inside the proven Recovery route {tuple(sorted(EXPECTED_ROUTE_IDS))!r}"
        )

    universe = ExtremeSkillUniverseService(database)
    animal_capacity = _capacity(universe, "Animal Companions")
    support_capacity = _capacity(universe, "Support")
    # The carrier is one normal active skill. Represent it as a one-normal, no-Ultimate
    # capacity so the shared 5-normal + 1-Ultimate topology proof remains authoritative.
    carrier_capacity = type(animal_capacity)(CARRIER_LINE, 1, 0)

    baseline_bar_legal = _bar_shape_legal(
        ((BASELINE_ANIMAL_SLOTS, animal_capacity), (BASELINE_SUPPORT_SLOTS, support_capacity))
    )
    challenger_bar_legal = _bar_shape_legal(
        (
            (CHALLENGER_ANIMAL_SLOTS, animal_capacity),
            (CHALLENGER_SUPPORT_SLOTS, support_capacity),
            (CHALLENGER_MINOR_INTELLECT_SLOTS, carrier_capacity),
        )
    )
    if not baseline_bar_legal:
        unresolved.append("Corrected one-Animal/four-Support baseline bar is no longer legal")
    if not challenger_bar_legal:
        unresolved.append("One-Animal/three-Support/one-Minor-Intellect challenger bar is not legal")

    baseline_percent = float(args.baseline_percent)
    challenger_percent = baseline_percent - 10.0 + minor_percent
    pre_percent = float(args.pre_percent)
    baseline_final = pre_percent * (1.0 + baseline_percent / 100.0)
    challenger_final = pre_percent * (1.0 + challenger_percent / 100.0)
    challenger_lead = challenger_final - baseline_final

    common_major = float(args.common_major_intellect_percent)
    baseline_with_major = pre_percent * (1.0 + (baseline_percent + common_major) / 100.0)
    challenger_with_major = pre_percent * (1.0 + (challenger_percent + common_major) / 100.0)
    challenger_major_lead = challenger_with_major - baseline_with_major

    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        carrier is not None
        and self_usable
        and abs(minor_percent - 15.0) <= 1e-9
        and route_contains_carrier_line
        and baseline_bar_legal
        and challenger_bar_legal
        and challenger_lead > 0.0
        and challenger_major_lead > 0.0
        and not unique_unresolved
    )

    print("EXTREME MAGICKA RECOVERY MINOR INTELLECT ACTIVE-BAR COMPARISON")
    print(f"database={database}")
    print(f"carrier_name={CARRIER_NAME!r}")
    print(f"carrier_ability_id={carrier_id}")
    print(f"carrier_line={carrier_line!r}")
    print(f"carrier_self_usable={bool(self_usable)}")
    print(f"carrier_duration={float(self_usable[0].duration) if self_usable else 0.0:.3f}")
    print(f"minor_intellect_percent={minor_percent:.3f}")
    print(f"pre_percent={pre_percent:.3f}")
    print()
    print("NAMED-BUFF-FREE BASELINE")
    print(f"baseline_animal_slots={BASELINE_ANIMAL_SLOTS}")
    print(f"baseline_support_slots={BASELINE_SUPPORT_SLOTS}")
    print(f"baseline_total_percent={baseline_percent:.3f}")
    print(f"baseline_final={baseline_final:.3f}")
    print()
    print("MINOR INTELLECT CHALLENGER")
    print(f"challenger_animal_slots={CHALLENGER_ANIMAL_SLOTS}")
    print(f"challenger_support_slots={CHALLENGER_SUPPORT_SLOTS}")
    print(f"challenger_minor_intellect_slots={CHALLENGER_MINOR_INTELLECT_SLOTS}")
    print(f"challenger_total_percent={challenger_percent:.3f}")
    print(f"challenger_final={challenger_final:.3f}")
    print(f"challenger_lead={challenger_lead:.3f}")
    print()
    print("COMMON MAJOR INTELLECT CONTEXT")
    print(f"common_major_intellect_percent={common_major:.3f}")
    print(f"baseline_with_major_intellect={baseline_with_major:.3f}")
    print(f"challenger_with_major_intellect={challenger_with_major:.3f}")
    print(f"challenger_major_intellect_lead={challenger_major_lead:.3f}")
    print()
    print("PROOF GATES")
    print(f"carrier_in_proven_route={route_contains_carrier_line}")
    print(f"baseline_bar_legal={baseline_bar_legal}")
    print(f"challenger_bar_legal={challenger_bar_legal}")
    print(f"minor_intellect_semantics_proven={abs(minor_percent - 15.0) <= 1e-9}")
    print(f"challenger_beats_baseline={challenger_lead > 0.0}")
    print(f"challenger_beats_baseline_with_major_intellect={challenger_major_lead > 0.0}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"minor_intellect_bar_comparison_closed={closed}")
    if closed:
        print("NEXT_STEP=promote one-Animal/three-Support/Minor-Intellect bar and compose remaining contextual Recovery states")
    else:
        print("NEXT_STEP=close only the reported Minor Intellect bar blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
