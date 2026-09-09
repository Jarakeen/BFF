from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.settings_service import SettingsService
from tools.probe_esologs_events import PLAYER_QUERY, fetch_all_events, gql, json_scalar

DEFAULT_SUNSPIRE_REPORTS = (
    "v16hzgGWTV7BZ48f",
    "btZpy9j6KzYXkRL3",
    "FPy6Tc9BzwQNbfVK",
    "PCBxhWranVctf8Q2",
)
DEFAULT_DSR_CONTROL_REPORT = "6h4DjY8zNAxKMb2W"


def _client(settings_path: Path) -> EsoLogsClient:
    settings = SettingsService(settings_path).load()
    return EsoLogsClient(
        client_id=settings.get("EsoLogsClientId", ""),
        client_secret=settings.get("EsoLogsClientSecret", ""),
    )


def _matching_fights(
    client: EsoLogsClient,
    report_code: str,
    *,
    encounter_name: str,
) -> tuple[dict, ...]:
    fights = client.get_fights(report_code)
    key = encounter_name.casefold()
    return tuple(
        fight
        for fight in fights
        if key in str(fight.get("name") or "").casefold()
    )


def _player_details(
    client: EsoLogsClient,
    *,
    report_code: str,
    fight_id: int,
    start: float,
    end: float,
):
    data = gql(
        client,
        PLAYER_QUERY,
        {
            "code": report_code,
            "fightIDs": [fight_id],
            "startTime": start,
            "endTime": end,
        },
    )
    report = (data.get("reportData") or {}).get("report") or {}
    return json_scalar(report.get("playerDetails")) or {}


def pull_corpus(
    *,
    client: EsoLogsClient,
    report_codes: tuple[str, ...],
    encounter_name: str = "Lokkestiiz",
    include_resources: bool = True,
    event_limit: int = 10000,
) -> dict:
    corpus: dict = {
        "schema_version": 1,
        "encounter": encounter_name.casefold(),
        "reports": {},
    }

    for raw_code in report_codes:
        code = EsoLogsClient.normalize_report_code(raw_code)
        fights = _matching_fights(client, code, encounter_name=encounter_name)
        report_row = {"matching_fight_count": len(fights), "fights": {}}
        corpus["reports"][code] = report_row

        for fight in fights:
            fight_id = int(fight["id"])
            start = float(fight["startTime"])
            end = float(fight["endTime"])
            events = fetch_all_events(
                client,
                code,
                fight_id,
                start,
                end,
                include_resources=include_resources,
                limit=max(100, min(int(event_limit), 10000)),
            )
            report_row["fights"][str(fight_id)] = {
                "metadata": fight,
                "player_details": _player_details(
                    client,
                    report_code=code,
                    fight_id=fight_id,
                    start=start,
                    end=end,
                ),
                "event_count": len(events),
                "events": events,
            }

    return corpus


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Pull a read-only Lokkestiiz ESO Logs corpus using the same BFF credentials "
            "already configured for ESO Logs Trending."
        )
    )
    parser.add_argument(
        "--report",
        action="append",
        dest="reports",
        help="Sunspire report code or URL. Repeat to override the built-in four-report corpus.",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path("settings.json"),
        help="BFF settings path; the ESO Logs secret is resolved by SettingsService/keyring.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("research/raw/lokkestiiz_corpus.json"),
    )
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--no-resources", action="store_true")
    args = parser.parse_args()

    reports = tuple(args.reports or DEFAULT_SUNSPIRE_REPORTS)
    client = _client(args.settings)

    try:
        corpus = pull_corpus(
            client=client,
            report_codes=reports,
            encounter_name="Lokkestiiz",
            include_resources=not args.no_resources,
            event_limit=args.limit,
        )
    except EsoLogsApiError as exc:
        print(f"ESO Logs error: {exc}")
        return 2

    destination = args.out
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_fights = 0
    total_events = 0
    print("LOKKESTIIZ ESO LOGS CORPUS")
    for code, report in corpus["reports"].items():
        count = int(report["matching_fight_count"])
        total_fights += count
        report_events = sum(
            int(fight.get("event_count", 0)) for fight in report["fights"].values()
        )
        total_events += report_events
        print(f"REPORT: {code} lokkestiiz_fights={count} events={report_events:,}")
    print(f"TOTAL_FIGHTS: {total_fights}")
    print(f"TOTAL_EVENTS: {total_events:,}")
    print(f"OUTPUT: {destination}")
    print(f"DSR_CONTROL_REPORT_NOT_INCLUDED: {DEFAULT_DSR_CONTROL_REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
