from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_meteor_esologs_timing_signature_candidate_service import (
    RotationMeteorEsoLogsTimingSignatureCandidateService,
)
from tools.discover_esologs_runtime_db import discover


def _resolve_logs_database(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    candidates = discover(
        roots=(
            Path(get_data_dir()),
            ROOT / "data",
            ROOT / "user_data",
            ROOT / "research",
        )
    )
    if not candidates:
        print("No ESO Logs runtime database discovered. Use --logs-db to specify one.")
        return None
    if len(candidates) > 1:
        preferred = tuple(path for path in candidates if path.name == "eso_gear_customization_test.db")
        if len(preferred) == 1:
            return preferred[0]
        print("Multiple ESO Logs runtime databases discovered:")
        for path in candidates:
            print(f"- {path}")
        print("Use --logs-db to choose one explicitly.")
        return None
    return candidates[0]


def audit(logs_database_path: Path, *, max_candidates: int = 20) -> int:
    report = RotationMeteorEsoLogsTimingSignatureCandidateService(logs_database_path).inspect()

    print("=" * 72)
    print(" METEOR-LIKE ESO LOGS TIMING SIGNATURE CANDIDATE REVIEW")
    print("=" * 72)
    print(f"Database: {logs_database_path}")
    print("Filter: anonymous damage streams with ~1s cadence and <=11.5s run span")
    print(f"Candidates: {len(report.candidates)}")
    print()
    print("Ranked candidates:")
    if not report.candidates:
        print("- none")
    else:
        for candidate in report.candidates[:max_candidates]:
            names = " | ".join(candidate.ability_names) if candidate.ability_names else "(unnamed)"
            print(
                f"- id={candidate.ability_game_id} | {names} | sources={candidate.source_actor_count} "
                f"| events={candidate.event_count} | occurrences={candidate.occurrence_count} "
                f"| 1s-matches={candidate.one_second_interval_matches}"
            )
            print(
                "  median interval="
                + (f"{candidate.median_interval_seconds:.4f}s" if candidate.median_interval_seconds is not None else "n/a")
                + " | median span="
                + (f"{candidate.median_run_span_seconds:.4f}s" if candidate.median_run_span_seconds is not None else "n/a")
                + " | max span="
                + (f"{candidate.maximum_run_span_seconds:.4f}s" if candidate.maximum_run_span_seconds is not None else "n/a")
            )

    if report.unresolved:
        print()
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print()
    print("Interpretation guardrails:")
    print("- matching timing does not identify a candidate as Meteor")
    print("- ability ids remain observational ESO Logs handles")
    print("- this audit never promotes runtime semantics")
    return 0 if report.candidates else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find anonymous ESO Logs damage streams resembling Meteor's reviewed 11s / 1s DoT timing.")
    parser.add_argument("--logs-db", type=Path, help="Optional explicit ESO Logs SQLite database")
    parser.add_argument("--max-candidates", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logs_db = _resolve_logs_database(args.logs_db)
    if logs_db is None:
        return 2
    return audit(logs_db, max_candidates=args.max_candidates)


if __name__ == "__main__":
    raise SystemExit(main())
