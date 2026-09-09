from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_healer_esologs_ability_family_service import (
    RotationHealerEsoLogsAbilityFamilyService,
)
from services.rotation_healer_esologs_observation_extractor import (
    DF_HEALER_U50_OBSERVATION_TARGETS,
)
from services.rotation_healer_esologs_sqlite_family_match_service import (
    RotationHealerEsoLogsSqliteFamilyMatchService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Match historical healer ESO Logs ability ids to current canonical "
            "skill families. Read-only; no runtime timing is promoted."
        )
    )
    parser.add_argument("--log-db", required=True, help="historical ESO Logs SQLite database")
    parser.add_argument(
        "--canonical-db",
        default="data/eso.db",
        help="current canonical ESO database (default: data/eso.db)",
    )
    return parser


def render_report(report, *, canonical_db: Path) -> str:
    family_service = RotationHealerEsoLogsAbilityFamilyService(canonical_db)
    lines = [
        "================================================================",
        " PHASE 13 HEALER ESO LOGS ABILITY-FAMILY MATCH",
        "================================================================",
        f"Log DB:       {report.log_database_path}",
        f"Canonical DB: {report.canonical_database_path}",
        "Boundary: family identity only; no runtime timing is promoted",
        "",
        "TARGET FAMILIES",
        "---------------",
    ]
    for target in DF_HEALER_U50_OBSERVATION_TARGETS:
        family = family_service.resolve(target.source_name)
        if family is None:
            lines.append(f"- {target.source_name}: unresolved")
        else:
            ids = ", ".join(str(value) for value in family.ability_game_ids)
            lines.append(f"- {target.source_name}: skill_id={family.skill_id} ability_ids=[{ids}]")

    lines.extend(["", "HISTORICAL MATCHES", "------------------"])
    if report.matches:
        for item in report.matches:
            ids = ", ".join(str(value) for value in item.matched_ability_ids)
            lines.append(
                f"- report={item.report_code} fight={item.fight_id} actor={item.actor_id} "
                f"{item.source_name}: ids=[{ids}] events={item.event_count} "
                f"periodic={item.periodic_event_count}"
            )
    else:
        lines.append("none")

    lines.extend(["", "REPORT UNRESOLVED", "-----------------"])
    if report.unresolved:
        lines.extend(f"- {item}" for item in report.unresolved)
    else:
        lines.append("none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    canonical_db = Path(args.canonical_db)
    report = RotationHealerEsoLogsSqliteFamilyMatchService().inspect(
        Path(args.log_db),
        canonical_db,
    )
    print(render_report(report, canonical_db=canonical_db))
    return 0 if not report.unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
