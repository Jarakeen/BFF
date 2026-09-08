from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_healer_esologs_sqlite_discovery_service import (
    RotationHealerEsoLogsSqliteDiscoveryService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect an imported ESO Logs SQLite database for reports, fights, "
            "healer actors, and reviewed DF-healer HoT evidence. Read-only."
        )
    )
    parser.add_argument("--db", required=True, help="SQLite database to inspect")
    return parser


def render_report(report) -> str:
    lines = [
        "================================================================",
        " PHASE 13 HEALER ESO LOGS SQLITE DISCOVERY",
        "================================================================",
        f"Database: {report.database_path}",
        f"log_event: {'yes' if report.has_log_event else 'no'}",
        f"log_actor: {'yes' if report.has_log_actor else 'no'}",
        "Boundary: discovery only; no runtime timing is promoted",
        "",
        "FIGHTS",
        "------",
    ]
    if report.fights:
        for fight in report.fights:
            first = "n/a" if fight.first_timestamp is None else f"{fight.first_timestamp:g}"
            last = "n/a" if fight.last_timestamp is None else f"{fight.last_timestamp:g}"
            lines.append(
                f"- report={fight.report_code} fight={fight.fight_id} "
                f"events={fight.event_count} time={first}..{last}"
            )
    else:
        lines.append("none")

    lines.extend(["", "HEALERS", "-------"])
    if report.healers:
        for healer in report.healers:
            identity = healer.display_name or healer.name or "<unnamed>"
            abilities = ", ".join(healer.target_ability_names) or "none of the five target HoTs"
            lines.append(
                f"- report={healer.report_code} fight={healer.fight_id} "
                f"actor={healer.actor_id} name={identity}: {abilities}"
            )
    else:
        lines.append("none")

    lines.extend(["", "REPORT UNRESOLVED", "-----------------"])
    lines.extend(f"- {item}" for item in report.unresolved) if report.unresolved else lines.append("none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = RotationHealerEsoLogsSqliteDiscoveryService().inspect(Path(args.db))
    print(render_report(report))
    return 0 if report.has_log_event else 1


if __name__ == "__main__":
    raise SystemExit(main())
