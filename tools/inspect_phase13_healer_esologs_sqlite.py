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
            "healer actors, target HoTs, and the healer's actual cast/heal ability ids. Read-only."
        )
    )
    parser.add_argument("--db", required=True, help="SQLite database to inspect")
    parser.add_argument(
        "--ability-limit",
        type=int,
        default=12,
        help="maximum observed cast/heal abilities to print per healer/fight (default: 12)",
    )
    return parser


def render_report(report, *, ability_limit: int = 12) -> str:
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
        limit = max(0, int(ability_limit))
        for healer in report.healers:
            identity = healer.display_name or healer.name or "<unnamed>"
            targets = ", ".join(healer.target_ability_names) or "none of the five target HoTs"
            lines.append(
                f"- report={healer.report_code} fight={healer.fight_id} "
                f"actor={healer.actor_id} name={identity}: {targets}"
            )
            if not healer.observed_abilities:
                lines.append("    observed cast/heal abilities: none")
                continue
            lines.append("    observed cast/heal abilities:")
            for ability in healer.observed_abilities[:limit]:
                name = ability.ability_name or "<name unavailable>"
                event_types = ",".join(ability.event_types)
                lines.append(
                    f"      - id={ability.ability_game_id} name={name} "
                    f"events={ability.event_count} periodic={ability.periodic_event_count} "
                    f"types={event_types}"
                )
            if len(healer.observed_abilities) > limit:
                lines.append(
                    f"      ... {len(healer.observed_abilities) - limit} more; rerun with --ability-limit"
                )
    else:
        lines.append("none")

    lines.extend(["", "REPORT UNRESOLVED", "-----------------"])
    lines.extend(f"- {item}" for item in report.unresolved) if report.unresolved else lines.append("none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = RotationHealerEsoLogsSqliteDiscoveryService().inspect(Path(args.db))
    print(render_report(report, ability_limit=args.ability_limit))
    return 0 if report.has_log_event else 1


if __name__ == "__main__":
    raise SystemExit(main())
