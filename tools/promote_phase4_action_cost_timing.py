from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.resource_cost_timing import CostTimingKind, resolve_action_cost_timing


DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def _table_columns(connection: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in connection.execute("PRAGMA table_info(ability)")}


def build_promotion_plan(connection: sqlite3.Connection) -> dict[str, object]:
    connection.row_factory = sqlite3.Row
    columns = _table_columns(connection)
    rows = connection.execute(
        """
        SELECT ability_id, name, base_cost, raw_json
        FROM ability
        WHERE base_cost > 0
        ORDER BY ability_id
        """
    ).fetchall()

    recurring = 0
    activation = 0
    unresolved: list[dict[str, object]] = []
    values: list[tuple[int, str | None, int]] = []

    for row in rows:
        try:
            raw = json.loads(row["raw_json"] or "{}")
            timing = resolve_action_cost_timing(
                base_is_cost_time=raw.get("baseIsCostTime"),
                charge_freq=raw.get("chargeFreq"),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            unresolved.append(
                {
                    "ability_id": row["ability_id"],
                    "name": row["name"],
                    "reason": str(exc),
                }
            )
            continue

        is_recurring = int(timing.kind is CostTimingKind.RECURRING)
        if is_recurring:
            recurring += 1
        else:
            activation += 1

        charge_freq_raw = raw.get("chargeFreq")
        charge_freq_text = None if charge_freq_raw in (None, "") else str(charge_freq_raw)
        values.append((is_recurring, charge_freq_text, int(row["ability_id"])))

    return {
        "positive_cost_rows": len(rows),
        "activation_rows": activation,
        "recurring_rows": recurring,
        "unresolved_rows": len(unresolved),
        "unresolved": unresolved,
        "needs_base_is_cost_time_column": "base_is_cost_time" not in columns,
        "needs_charge_freq_raw_column": "charge_freq_raw" not in columns,
        "values": values,
    }


def apply_promotion(connection: sqlite3.Connection, plan: dict[str, object]) -> None:
    if plan["unresolved_rows"]:
        raise RuntimeError("Refusing to promote action-cost timing with unresolved rows")

    if plan["needs_base_is_cost_time_column"]:
        connection.execute(
            "ALTER TABLE ability ADD COLUMN base_is_cost_time INTEGER DEFAULT 0"
        )
    if plan["needs_charge_freq_raw_column"]:
        connection.execute("ALTER TABLE ability ADD COLUMN charge_freq_raw TEXT")

    connection.executemany(
        """
        UPDATE ability
        SET base_is_cost_time = ?, charge_freq_raw = ?
        WHERE ability_id = ?
        """,
        plan["values"],
    )


def _print_report(plan: dict[str, object], *, write: bool) -> None:
    print("========================================")
    print(" PHASE 4 ACTION COST TIMING PROMOTION")
    print("========================================")
    print(f"Mode:                         {'WRITE' if write else 'DRY RUN'}")
    print(f"Positive-cost rows:           {plan['positive_cost_rows']}")
    print(f"Activation rows:              {plan['activation_rows']}")
    print(f"Recurring rows:               {plan['recurring_rows']}")
    print(f"Unresolved rows:              {plan['unresolved_rows']}")
    print(f"Add base_is_cost_time column: {plan['needs_base_is_cost_time_column']}")
    print(f"Add charge_freq_raw column:   {plan['needs_charge_freq_raw_column']}")
    print()
    if plan["unresolved"]:
        print("UNRESOLVED")
        print("----------")
        for entry in plan["unresolved"]:
            print(entry)
    elif write:
        print("Promotion applied and committed.")
    else:
        print("No database changes made. Re-run with --write only after reviewing this plan.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote verified Phase 4 action-cost timing fields from ability.raw_json."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply schema/data changes. Default is read-only dry run.",
    )
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    try:
        plan = build_promotion_plan(connection)
        _print_report(plan, write=args.write)
        if plan["unresolved_rows"]:
            return 1
        if args.write:
            apply_promotion(connection, plan)
            connection.commit()
        return 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
