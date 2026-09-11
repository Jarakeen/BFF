from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_heavy_attack_restore_esologs_evidence_service import (
    RotationHeavyAttackRestoreEsoLogsEvidenceService,
)


def _amount_summary(observations):
    counter = Counter(float(item.resource_change) for item in observations)
    return tuple(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _print_alias_candidates(rows, *, limit: int) -> None:
    print("POSITIVE RESOURCE-CHANGE ABILITY ALIASES")
    print("----------------------------------------")
    if not rows:
        print("none")
        return
    for item in rows[:limit]:
        print(
            f"{item.event_count:5d} events | source={item.source_id} | "
            f"ability={item.ability_name or '(unnamed)'} [{item.ability_game_id}] | "
            f"resource_type={item.resource_change_type} | "
            f"restore_range={item.minimum_restore:g}..{item.maximum_restore:g}"
        )
    if len(rows) > limit:
        print(f"... {len(rows) - limit} additional aliases omitted")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search imported ESO Logs resource-change events for fully charged heavy-attack "
            "candidate evidence. Results remain observational until reviewed."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--ability-name",
        action="append",
        default=[],
        help="reviewed ESO Logs heavy-attack ability name alias; may be supplied more than once",
    )
    parser.add_argument(
        "--ability-id",
        type=int,
        action="append",
        default=[],
        help="reviewed ESO Logs numeric ability alias; observational only",
    )
    parser.add_argument(
        "--actor-name",
        action="append",
        default=[],
        help="reviewed character or account/display name used to discover raw ESO Logs source ids",
    )
    parser.add_argument(
        "--list-aliases",
        action="store_true",
        help="list positive resource-change ability aliases for the resolved actor/source ids",
    )
    parser.add_argument("--source-id", type=int, default=None)
    parser.add_argument("--report-code", default=None)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    if int(args.limit) <= 0:
        raise ValueError("--limit must be positive")

    service = RotationHeavyAttackRestoreEsoLogsEvidenceService()
    source_ids: list[int] = []
    actor_rows = ()
    if args.actor_name:
        actor_rows = service.discover_actor_aliases(
            Path(args.database),
            actor_names=tuple(args.actor_name),
            report_code=args.report_code,
        )
        source_ids.extend(row.actor_id for row in actor_rows)
    if args.source_id is not None:
        source_ids.append(int(args.source_id))
    source_ids = sorted(set(source_ids))

    if args.list_aliases:
        if not source_ids:
            raise ValueError(
                "--list-aliases requires a resolved --actor-name or explicit --source-id"
            )
        rows = service.discover_positive_resource_aliases(
            Path(args.database),
            source_ids=tuple(source_ids),
            report_code=args.report_code,
        )
        print("=" * 112)
        print(" PHASE 13 ESO LOGS HEAVY-ATTACK ALIAS DISCOVERY")
        print("=" * 112)
        print("Evidence status: CANDIDATE OBSERVATION ONLY")
        if actor_rows:
            print("Resolved actors:")
            for row in actor_rows:
                print(
                    f"  report={row.report_code} fight={row.fight_id} actor={row.actor_id} "
                    f"name={row.name!r} display={row.display_name!r}"
                )
        print(f"Source ids:        {', '.join(str(value) for value in source_ids)}")
        print(f"Report filter:     {args.report_code or 'all imported reports'}")
        print()
        _print_alias_candidates(rows, limit=int(args.limit))
        print()
        print("BOUNDARY")
        print("--------")
        print("- This is alias discovery, not heavy-attack identity promotion.")
        print("- Resource type values and numeric ability ids remain raw ESO Logs evidence.")
        print("- Review a plausible heavy-attack alias before running restore-amount discovery.")
        return 0 if rows else 3

    if not args.ability_name and not args.ability_id:
        raise ValueError(
            "supply at least one reviewed --ability-name or --ability-id alias, "
            "or use --list-aliases with --actor-name/--source-id"
        )

    source_filter = args.source_id
    if source_filter is None and len(source_ids) == 1:
        source_filter = source_ids[0]
    elif source_filter is None and len(source_ids) > 1:
        raise ValueError(
            "actor-name resolution produced multiple raw source ids; rerun with --report-code "
            "or an explicit --source-id before promoting an ability alias"
        )

    report = service.discover_corpus(
        Path(args.database),
        ability_names=tuple(args.ability_name),
        ability_game_ids=tuple(args.ability_id),
        source_id=source_filter,
        report_code=args.report_code,
    )

    print("=" * 112)
    print(" PHASE 13 ESO LOGS HEAVY-ATTACK RESTORE OBSERVATION AUDIT")
    print("=" * 112)
    print("Evidence status: CANDIDATE OBSERVATION ONLY")
    print(
        "Reviewed aliases: "
        + ", ".join(
            [*(repr(value) for value in args.ability_name), *(str(value) for value in args.ability_id)]
        )
    )
    print(f"Source filter:     {source_filter if source_filter is not None else 'any'}")
    print(f"Report filter:     {args.report_code or 'all imported reports'}")
    print(f"Matches:           {len(report.observations)}")
    print()

    if report.unresolved:
        print("UNRESOLVED")
        print("----------")
        for item in report.unresolved:
            print(f"- {item}")
        return 3

    print("OBSERVED RESTORE AMOUNTS")
    print("------------------------")
    for amount, count in _amount_summary(report.observations):
        print(f"{amount:10g} | {count:4d} event{'s' if count != 1 else ''}")

    print()
    print("EVENT PROVENANCE")
    print("----------------")
    for item in report.observations[: int(args.limit)]:
        print(
            f"{item.resource_change:10g} | report={item.report_code} fight={item.fight_id} "
            f"event={item.event_index} time={item.timestamp:g} source={item.source_id} "
            f"ability={item.ability_name or '(unnamed)'} [{item.ability_game_id}] "
            f"resource_type={item.resource_change_type} waste={item.waste} "
            f"max_resource={item.max_resource_amount}"
        )
    if len(report.observations) > int(args.limit):
        print(f"... {len(report.observations) - int(args.limit)} additional observations omitted")

    print()
    print("BOUNDARY")
    print("--------")
    print("- Frequency is not canonical proof.")
    print("- Numeric ability ids and resource type values remain raw ESO Logs evidence.")
    print("- Review the source actor, ability alias, waste, and resource type before promotion.")
    print("- This audit never writes to the ESO database and never updates heavy-restore constants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
