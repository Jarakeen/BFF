from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
)
from services.rotation_scalding_rune_magnitude_multistate_signature_service import (
    RotationScaldingRuneMagnitudeMultistateSignatureService,
)
from tools.discover_esologs_runtime_db import discover


SKILL = "scalding_rune"
PERIODIC_ID = 40468


def _logs_database(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    matches = discover(
        roots=(get_data_dir(), ROOT / "data", ROOT / "user_data", ROOT / "research")
    )
    if not matches:
        raise RuntimeError("no ESO Logs runtime database was found")
    if len(matches) > 1:
        rendered = "\n".join(f"  - {path}" for path in matches)
        raise RuntimeError(
            "multiple ESO Logs runtime databases were found; pass --logs-db explicitly:\n"
            + rendered
        )
    return matches[0]


def _factor_text(factor) -> str:
    identity = factor.ability_name or (
        str(factor.ability_game_id) if factor.ability_game_id is not None else "unknown"
    )
    return f"{factor.actor_scope}:{factor.event_type}:{identity}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Scalding Rune ESO Logs review of repeated multi-state signatures "
            "around amount-changing 40468 periodic occurrences."
        )
    )
    parser.add_argument("--logs-db")
    parser.add_argument("--canonical-db", default=str(DEFAULT_DATABASE))
    parser.add_argument("--minimum-samples", type=int, default=2)
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()

    try:
        logs_db = _logs_database(args.logs_db)
        canonical_db = Path(args.canonical_db)
        transitions = RotationDDPeriodicEsoLogsMagnitudeStateTransitionService(
            canonical_database_path=canonical_db,
            logs_database_path=logs_db,
        ).inspect(SKILL, periodic_ability_id=PERIODIC_ID)
        report = RotationScaldingRuneMagnitudeMultistateSignatureService().analyze(
            transitions,
            minimum_samples=args.minimum_samples,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print("=" * 76)
    print(" SCALDING RUNE ESO LOGS MULTI-STATE MAGNITUDE SIGNATURE REVIEW")
    print("=" * 76)
    print(f"Logs database: {logs_db}")
    print(f"Canonical database: {canonical_db}")
    print(f"Periodic evidence id: {PERIODIC_ID}")
    print(f"Minimum repeated-signature samples: {max(1, args.minimum_samples)}")
    print()
    print(f"Amount-changing transitions: {report.transition_count}")
    print(f"Multi-state amount-changing transitions: {report.multistate_transition_count}")
    print(f"Repeated signatures retained: {len(report.signatures)}")
    print(f"Reversible signature pairs retained: {report.reversible_signature_pairs}")
    print()
    print("Ranked repeated signatures:")
    if not report.signatures:
        print("- none")
    for index, summary in enumerate(report.signatures[: max(0, args.max_results)], start=1):
        direction = (
            "consistent increase"
            if summary.amount_increased == summary.sample_count
            else "consistent decrease"
            if summary.amount_decreased == summary.sample_count
            else "mixed"
        )
        print(
            f"[{index}] samples={summary.sample_count} direction={direction} "
            f"increase/decrease={summary.amount_increased}/{summary.amount_decreased}"
        )
        print(
            f"    ratio median/min/max: {summary.median_ratio:.6f} / "
            f"{summary.minimum_ratio:.6f} / {summary.maximum_ratio:.6f}"
        )
        for factor in summary.factors:
            print(f"    - {_factor_text(factor)}")

    if report.unresolved:
        print("\nUnresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print("\nInterpretation guardrails:")
    print("- repeated signatures are observational correlations, not causal proof")
    print("- exact state sets may still omit unlogged or unmodeled combat inputs")
    print("- reversible signatures strengthen review only when damage response is likewise coherent")
    print("- this audit never promotes Scalding Rune magnitude policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
