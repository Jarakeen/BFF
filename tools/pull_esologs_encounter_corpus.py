from __future__ import annotations

"""Pull a read-only ESO Logs corpus for one named encounter."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_client import EsoLogsApiError
from tools.pull_lokkestiiz_corpus import _client, pull_corpus


def pull_and_write(
    *,
    encounter_name: str,
    report_codes: tuple[str, ...],
    settings_path: Path,
    destination: Path,
    event_limit: int = 10000,
    include_resources: bool = True,
) -> dict:
    name = str(encounter_name or "").strip()
    if not name:
        raise ValueError("encounter name cannot be empty")
    if not report_codes:
        raise ValueError("at least one ESO Logs report is required")

    client = _client(settings_path)
    corpus = pull_corpus(
        client=client,
        report_codes=tuple(report_codes),
        encounter_name=name,
        include_resources=include_resources,
        event_limit=event_limit,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return corpus


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Pull a read-only ESO Logs corpus for one named encounter using BFF's "
            "existing ESO Logs credentials."
        )
    )
    parser.add_argument(
        "--encounter",
        required=True,
        help="Encounter/boss name matched against ESO Logs fight names.",
    )
    parser.add_argument(
        "--report",
        action="append",
        required=True,
        help="ESO Logs report code or URL. Repeat for multiple reports.",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path("settings.json"),
        help="BFF settings path; ESO Logs credentials are resolved by SettingsService/keyring.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to research/raw/<encounter>_corpus.json.",
    )
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--no-resources", action="store_true")
    args = parser.parse_args()

    encounter = str(args.encounter).strip()
    safe_name = "_".join(encounter.casefold().split())
    destination = args.out or Path(f"research/raw/{safe_name}_corpus.json")

    try:
        corpus = pull_and_write(
            encounter_name=encounter,
            report_codes=tuple(args.report),
            settings_path=args.settings,
            destination=destination,
            event_limit=args.limit,
            include_resources=not args.no_resources,
        )
    except (EsoLogsApiError, OSError, ValueError) as exc:
        print(f"ESO Logs corpus error: {exc}")
        return 2

    total_fights = 0
    total_events = 0
    print(f"ESO LOGS ENCOUNTER CORPUS: {encounter}")
    for code, report in corpus["reports"].items():
        count = int(report["matching_fight_count"])
        total_fights += count
        report_events = sum(
            int(fight.get("event_count", 0))
            for fight in report["fights"].values()
        )
        total_events += report_events
        print(f"REPORT: {code} matching_fights={count} events={report_events:,}")
    print(f"TOTAL_FIGHTS: {total_fights}")
    print(f"TOTAL_EVENTS: {total_events:,}")
    print(f"OUTPUT: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
