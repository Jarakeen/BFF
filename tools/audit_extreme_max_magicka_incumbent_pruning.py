from __future__ import annotations

"""Proof-audit ordinary Max Magicka named gear against a legal incumbent.

This is deliberately not a canonical-score search. For Max Magicka, a mechanic-complete
ordinary gear breakpoint can only contribute exact flat Max Magicka in the current
reviewed objective adapter. Percentage, unresolved, and search-state-mutating effects
remain outside this proof bucket.

The audit solves the complete ordinary named-set breakpoint universe as a multiple-choice
0/1 knapsack over the 12 active-snapshot set-count units: each named set may be absent or
use exactly one reviewed breakpoint. The DP ignores physical slot restrictions, so its
maximum is an optimistic upper bound. If even that upper bound does not exceed the legal
incumbent package's exact flat gear contribution, every ordinary omitted package is
proof-dominated. Special/unresolved rows are reported separately and must be closed by
later targeted audits.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)

OBJECTIVE = "max_magicka"
TARGET = StatId.MAX_MAGICKA
ACTIVE_UNITS = 12
INCUMBENT_VALUE = 107574.0
INCUMBENT_PACKAGE = (
    ("Crafty Alfiq", 5),
    ("Necropotence", 4),
    ("Grace of the Ancients", 3),
)


@dataclass(frozen=True)
class Choice:
    set_id: int
    set_name: str
    count: int
    flat_delta: float


@dataclass(frozen=True)
class State:
    units: int
    flat_delta: float
    choices: tuple[Choice, ...]


def _flat_delta(row) -> float:
    total = 0.0
    for effect in row.candidate.source_effects:
        if effect.stat is TARGET and effect.operation is EffectOperation.ADD:
            total += float(effect.value)
    return float(total)


def _identity(state: State):
    return tuple((c.set_id, c.count) for c in state.choices)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=INCUMBENT_VALUE)
    args = parser.parse_args()

    database = Path(args.database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)

    ordinary_by_set: dict[int, list[Choice]] = {}
    special_rows = []
    for row in relevance.evidence:
        if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            continue
        if row.search_state_rule is not None or row.candidate.unresolved:
            special_rows.append(row)
            continue
        # Mechanic-complete Max Magicka rows must be exact flat target-resource effects.
        target_effects = tuple(e for e in row.candidate.source_effects if e.stat is TARGET)
        invalid = tuple(e for e in target_effects if e.operation is not EffectOperation.ADD)
        if invalid:
            raise RuntimeError(
                f"Mechanic-complete ordinary Max Magicka row has non-flat effect: "
                f"{row.set_name} {row.piece_count}pc"
            )
        delta = _flat_delta(row)
        if delta <= 0.0:
            continue
        ordinary_by_set.setdefault(int(row.set_id), []).append(
            Choice(int(row.set_id), row.set_name, int(row.piece_count), delta)
        )

    for rows in ordinary_by_set.values():
        rows.sort(key=lambda c: (c.count, -c.flat_delta, c.set_name.casefold(), c.set_id))

    incumbent_parts: list[Choice] = []
    evidence_by_name_count = {
        (row.set_name.casefold(), int(row.piece_count)): row
        for row in relevance.evidence
    }
    for name, count in INCUMBENT_PACKAGE:
        row = evidence_by_name_count.get((name.casefold(), int(count)))
        if row is None:
            raise RuntimeError(f"Incumbent breakpoint missing: {name} {count}pc")
        if row.candidate.unresolved or row.search_state_rule is not None:
            raise RuntimeError(f"Incumbent breakpoint is not ordinary mechanic-complete: {name} {count}pc")
        incumbent_parts.append(Choice(int(row.set_id), name, int(count), _flat_delta(row)))
    incumbent_gear_delta = sum(c.flat_delta for c in incumbent_parts)

    # Multiple-choice 0/1 knapsack: one breakpoint at most per named set.
    states: dict[int, State] = {0: State(0, 0.0, ())}
    for set_id in sorted(ordinary_by_set):
        options = ordinary_by_set[set_id]
        next_states = dict(states)
        for used, state in states.items():
            for choice in options:
                total_units = used + choice.count
                if total_units > ACTIVE_UNITS:
                    continue
                candidate = State(
                    total_units,
                    state.flat_delta + choice.flat_delta,
                    (*state.choices, choice),
                )
                current = next_states.get(total_units)
                if (
                    current is None
                    or candidate.flat_delta > current.flat_delta + 1e-9
                    or (
                        abs(candidate.flat_delta - current.flat_delta) <= 1e-9
                        and _identity(candidate) < _identity(current)
                    )
                ):
                    next_states[total_units] = candidate
        states = next_states

    best = max(
        states.values(),
        key=lambda s: (s.flat_delta, s.units, tuple((-c.count, c.set_id) for c in s.choices)),
    )
    ordinary_closed = best.flat_delta <= incumbent_gear_delta + 1e-9

    print("EXTREME MAX MAGICKA INCUMBENT PRUNING AUDIT")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"incumbent_canonical_value={args.incumbent:.3f}")
    print(f"active_snapshot_units={ACTIVE_UNITS}")
    print(f"relevance_denominator_proven={relevance.denominator_proven}")
    print(f"ordinary_named_sets={len(ordinary_by_set)}")
    print(f"ordinary_breakpoints={sum(len(v) for v in ordinary_by_set.values())}")
    print(f"special_or_unresolved_breakpoints={len(special_rows)}")
    print()
    print("INCUMBENT GEAR")
    print(f"incumbent_exact_flat_gear_delta={incumbent_gear_delta:.3f}")
    for choice in incumbent_parts:
        print(f"  {choice.set_name} {choice.count}pc -> {choice.flat_delta:.3f}")
    print()
    print("ORDINARY OPTIMISTIC UPPER BOUND")
    print(f"ordinary_best_flat_delta={best.flat_delta:.3f}")
    print(f"ordinary_best_units={best.units}")
    print("ordinary_best_abstract_package=" + ", ".join(
        f"{c.set_name} {c.count}pc ({c.flat_delta:.0f})" for c in best.choices
    ))
    print(f"ordinary_margin_vs_incumbent_gear={best.flat_delta - incumbent_gear_delta:.3f}")
    print(f"ordinary_omitted_packages_closed={ordinary_closed}")
    print()
    print("SPECIAL / UNRESOLVED SURVIVORS")
    for row in sorted(
        special_rows,
        key=lambda r: (-float(r.reviewed_delta), r.set_name.casefold(), int(r.piece_count)),
    ):
        rule = getattr(row.search_state_rule, "value", row.search_state_rule)
        print(
            f"  {row.set_name} {row.piece_count}pc reviewed_delta={row.reviewed_delta:g} "
            f"rule={rule or '<none>'} unresolved={len(row.candidate.unresolved)}"
        )
    print()
    print(
        "NEXT_STEP="
        + (
            "ordinary named gear is closed; canonically score only special/unresolved survivors against 107574"
            if ordinary_closed
            else "ordinary abstract upper bound beats incumbent; materialize and canonically score only the DP-winning/frontier ordinary packages"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
