from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from minmax.resource_cost_timing import CostTimingKind, resolve_action_cost_timing


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


def _positive_cost_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT ability_id, name, rank, morph, base_cost, base_mechanic, raw_json
        FROM ability
        WHERE base_cost > 0
        ORDER BY ability_id
        """
    ).fetchall()


def audit_database(database_path: str | Path) -> dict[str, object]:
    with sqlite3.connect(str(database_path)) as connection:
        rows = _positive_cost_rows(connection)

    recurring = 0
    activation = 0
    unresolved: list[dict[str, object]] = []
    interval_counts: Counter[float] = Counter()
    recurring_samples: list[dict[str, object]] = []

    for row in rows:
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except json.JSONDecodeError as exc:
            unresolved.append(
                {
                    "ability_id": row["ability_id"],
                    "name": row["name"],
                    "reason": f"invalid raw_json: {exc}",
                }
            )
            continue

        try:
            timing = resolve_action_cost_timing(
                base_is_cost_time=raw.get("baseIsCostTime"),
                charge_freq=raw.get("chargeFreq"),
            )
        except ValueError as exc:
            unresolved.append(
                {
                    "ability_id": row["ability_id"],
                    "name": row["name"],
                    "rank": row["rank"],
                    "morph": row["morph"],
                    "base_cost": row["base_cost"],
                    "base_mechanic": row["base_mechanic"],
                    "baseIsCostTime": raw.get("baseIsCostTime"),
                    "chargeFreq": raw.get("chargeFreq"),
                    "reason": str(exc),
                }
            )
            continue

        if timing.kind is CostTimingKind.RECURRING:
            recurring += 1
            assert timing.interval_seconds is not None
            interval_counts[timing.interval_seconds] += 1
            if len(recurring_samples) < 30:
                recurring_samples.append(
                    {
                        "ability_id": row["ability_id"],
                        "name": row["name"],
                        "rank": row["rank"],
                        "morph": row["morph"],
                        "base_cost": row["base_cost"],
                        "base_mechanic": row["base_mechanic"],
                        "interval_seconds": timing.interval_seconds,
                        "chargeFreq": raw.get("chargeFreq"),
                    }
                )
        else:
            activation += 1

    return {
        "positive_cost_rows": len(rows),
        "activation_rows": activation,
        "recurring_rows": recurring,
        "unresolved_rows": len(unresolved),
        "interval_counts": dict(sorted(interval_counts.items())),
        "recurring_samples": recurring_samples,
        "unresolved": unresolved,
    }


def _print_report(report: dict[str, object]) -> None:
    print("========================================")
    print(" PHASE 4 ACTION COST TIMING AUDIT")
    print("========================================")
    print(f"Positive-cost rows: {report['positive_cost_rows']}")
    print(f"Activation rows:    {report['activation_rows']}")
    print(f"Recurring rows:     {report['recurring_rows']}")
    print(f"Unresolved rows:    {report['unresolved_rows']}")

    print()
    print("RECURRING INTERVALS")
    print("-------------------")
    interval_counts = report["interval_counts"]
    if interval_counts:
        for interval, count in interval_counts.items():
            print(f"{interval:g}s: {count}")
    else:
        print("none")

    print()
    print("RECURRING SAMPLES")
    print("-----------------")
    samples = report["recurring_samples"]
    if samples:
        for sample in samples:
            print(sample)
    else:
        print("none")

    print()
    print("UNRESOLVED")
    print("----------")
    unresolved = report["unresolved"]
    if unresolved:
        for entry in unresolved:
            print(entry)
    else:
        print("none")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 4 action-cost timing coverage.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    report = audit_database(args.database)
    _print_report(report)
    return 1 if report["unresolved_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
