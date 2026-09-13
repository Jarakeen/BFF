from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_scalding_rune_magnitude_single_factor_evidence_service import (
    RotationScaldingRuneMagnitudeSingleFactorEvidenceService,
)
from tools.discover_esologs_runtime_db import discover


def _logs_database(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    roots = (
        get_data_dir(),
        ROOT / "data",
        ROOT / "user_data",
        ROOT / "research",
    )
    matches = discover(roots=roots)
    if not matches:
        raise RuntimeError("no ESO Logs runtime database was found")
    if len(matches) > 1:
        rendered = "\n".join(f"  - {path}" for path in matches)
        raise RuntimeError(
            "multiple ESO Logs runtime databases were found; pass --logs-db explicitly:\n"
            + rendered
        )
    return matches[0]


def _fmt(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Scalding Rune ESO Logs audit that ranks amount-changing "
            "periodic tick transitions with exactly one reconstructed net state change."
        )
    )
    parser.add_argument("--logs-db", help="Optional explicit ESO Logs SQLite corpus")
    parser.add_argument(
        "--canonical-db",
        default=str(get_data_dir() / "eso.db"),
        help="Canonical ESO database used to resolve Scalding Rune cast identity.",
    )
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args(argv)

    try:
        logs_db = _logs_database(args.logs_db)
        canonical_db = Path(args.canonical_db)
        report = RotationScaldingRuneMagnitudeSingleFactorEvidenceService(
            canonical_database_path=canonical_db,
            logs_database_path=logs_db,
        ).inspect()
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print("=" * 72)
    print(" SCALDING RUNE ESO LOGS SINGLE-FACTOR MAGNITUDE REVIEW")
    print("=" * 72)
    print(f"Logs database: {logs_db}")
    print(f"Canonical database: {canonical_db}")
    print(f"Periodic evidence id: {report.periodic_ability_id}")
    print()
    print(f"Comparable adjacent occurrence pairs: {report.comparable_occurrence_pairs}")
    print(f"State-same + amount-changed pairs: {report.state_same_amount_changed}")
    print(
        "One-state amount-changing transitions: "
        f"{report.single_factor_amount_change_transitions}"
    )
    print(
        "Multi-state amount-changing transitions: "
        f"{report.multi_factor_amount_change_transitions}"
    )

    print("\nRanked one-state factors:")
    if not report.summaries:
        print("- none")
    for index, item in enumerate(report.summaries[: max(0, int(args.max_results))], start=1):
        identity = item.ability_name or "unnamed effect"
        if item.ability_game_id is not None:
            identity += f" [{item.ability_game_id}]"
        consistency = "consistent" if item.directionally_consistent else "mixed"
        print(
            f"[{index}] {identity} | {item.state_event_type} | actor={item.affected_actor}"
        )
        print(
            f"    samples={item.sample_count} increases={item.amount_increase_count} "
            f"decreases={item.amount_decrease_count} direction={consistency}"
        )
        print(
            "    amount ratio min/median/max="
            f"{_fmt(item.minimum_amount_ratio)}/"
            f"{_fmt(item.median_amount_ratio)}/"
            f"{_fmt(item.maximum_amount_ratio)}"
        )

    if report.unresolved:
        print("\nUnresolved:")
        for item in report.unresolved:
            print(f"- {item}")

    print("\nInterpretation guardrails:")
    print("- one-state correlation is evidence, not proof of causality")
    print("- numeric effect IDs remain ESO Logs evidence handles")
    print("- this audit never promotes Scalding Rune magnitude policy")
    print("- state-same amount changes mean reconstructed buff/debuff state is incomplete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
