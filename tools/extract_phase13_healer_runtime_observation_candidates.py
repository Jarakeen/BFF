from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter
from services.rotation_healer_esologs_observation_extractor import (
    DF_HEALER_U50_OBSERVATION_TARGETS,
    RotationHealerEsoLogsObservationExtractor,
    RotationHealerEsoLogsTimestampUnit,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract candidate healer HoT activation/tick observations from a raw "
            "ESO Logs JSON fight or multi-report research corpus. Output remains "
            "candidate evidence until reviewed."
        )
    )
    parser.add_argument("--raw", required=True, help="raw ESO Logs JSON export or research corpus")
    parser.add_argument("--fight-id", required=True, type=int, help="fight id inside the selected report")
    parser.add_argument(
        "--report-code",
        default=None,
        help="ESO Logs report code; required when --raw is a multi-report corpus",
    )
    parser.add_argument(
        "--caster-id",
        type=int,
        default=None,
        help="ESO Logs sourceID for the healer; omit with --list-casters",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="candidate observation JSON output path; required unless --list-casters",
    )
    parser.add_argument(
        "--list-casters",
        action="store_true",
        help="discover sourceIDs that cast or produced healing from the tracked healer HoTs",
    )
    parser.add_argument("--db", default="data/eso.db", help="canonical ESO database path")
    parser.add_argument(
        "--timestamp-unit",
        choices=[item.value for item in RotationHealerEsoLogsTimestampUnit],
        default=RotationHealerEsoLogsTimestampUnit.MILLISECONDS.value,
        help="raw event timestamp unit (default: milliseconds)",
    )
    parser.add_argument("--game-version", default="U50", help="game-version label stored in candidate evidence")
    return parser


def _candidate_caster_rows(
    events,
    targets=DF_HEALER_U50_OBSERVATION_TARGETS,
    *,
    alias_map: dict[str, tuple[int, ...]] | None = None,
):
    target_by_id: dict[int, str] = {}
    for target in targets:
        ids = (
            alias_map.get(target.source_name, ())
            if alias_map is not None
            else (int(target.ability_game_id),)
        )
        for ability_id in ids:
            target_by_id[int(ability_id)] = target.source_name

    stats = defaultdict(lambda: {"casts": 0, "heals": 0, "abilities": set()})

    for event in events:
        source_id = getattr(event, "source_id", None)
        ability_id = getattr(event, "ability_game_id", None)
        if source_id is None or ability_id is None:
            continue
        source_name = target_by_id.get(int(ability_id))
        if source_name is None:
            continue

        event_kind = getattr(event, "event_kind", None)
        if event_kind is SemanticEventKind.CAST:
            stats[int(source_id)]["casts"] += 1
        elif event_kind is SemanticEventKind.HEAL:
            stats[int(source_id)]["heals"] += 1
        else:
            continue
        stats[int(source_id)]["abilities"].add(source_name)

    rows = []
    for source_id, values in stats.items():
        rows.append(
            {
                "source_id": int(source_id),
                "casts": int(values["casts"]),
                "heals": int(values["heals"]),
                "abilities": tuple(sorted(values["abilities"], key=str.casefold)),
            }
        )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                -len(row["abilities"]),
                -row["casts"],
                -row["heals"],
                row["source_id"],
            ),
        )
    )


def _list_candidate_casters(
    raw_path: Path,
    *,
    fight_id: int,
    report_code: str | None = None,
    database_path: Path = Path("data/eso.db"),
) -> int:
    extractor = RotationHealerEsoLogsObservationExtractor(database_path)
    fight = extractor.load_fight(
        raw_path,
        fight_id=int(fight_id),
        report_code=report_code,
    )
    events = tuple(EsoLogsJsonEventInterpreter(fight).iter_events())
    alias_map = extractor.target_alias_map()
    rows = _candidate_caster_rows(events, alias_map=alias_map)

    print("================================================================")
    print(" PHASE 13 HEALER ESO LOGS CASTER DISCOVERY")
    print("================================================================")
    print(f"Raw export:     {raw_path}")
    print(f"Report / fight: {fight.report_code} / {fight.fight_id}")
    print("Canonical skill aliases:")
    for target in DF_HEALER_U50_OBSERVATION_TARGETS:
        aliases = alias_map.get(target.source_name, ())
        print(
            f"- {target.canonical_skill_id or target.source_name}: "
            + ", ".join(str(value) for value in aliases)
        )
    print()
    if not rows:
        print("No sourceID cast or produced healing from the tracked healer HoTs across canonical aliases.")
        return 1

    print("Candidate sourceIDs (best coverage first):")
    for row in rows:
        abilities = ", ".join(row["abilities"])
        print(
            f"- sourceID={row['source_id']} | abilities={len(row['abilities'])} "
            f"| casts={row['casts']} | heals={row['heals']} | {abilities}"
        )
    print()
    print(
        "Use the sourceID with the strongest healer-HoT coverage as --caster-id. "
        "Canonical lower-snake-case skill identity owns matching; numeric ESO ids are "
        "aliases resolved from the database and are not treated as semantic identity."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_casters:
        return _list_candidate_casters(
            Path(args.raw),
            fight_id=args.fight_id,
            report_code=args.report_code,
            database_path=Path(args.db),
        )
    if args.caster_id is None:
        parser.error("--caster-id is required unless --list-casters is used")
    if not args.out:
        parser.error("--out is required unless --list-casters is used")

    report = RotationHealerEsoLogsObservationExtractor(Path(args.db)).extract(
        Path(args.raw),
        fight_id=args.fight_id,
        caster_id=args.caster_id,
        report_code=args.report_code,
        timestamp_unit=args.timestamp_unit,
        game_version=args.game_version,
    )
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            report.to_candidate_fixture_payload(game_version=args.game_version),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("================================================================")
    print(" PHASE 13 HEALER ESO LOGS OBSERVATION CANDIDATE EXTRACTION")
    print("================================================================")
    print(f"Raw export:      {report.source_path}")
    print(f"Report / fight:  {report.report_code} / {report.fight_id}")
    print(f"Caster sourceID: {report.caster_id}")
    print(f"Timestamp unit:  {report.timestamp_unit.value}")
    print(f"Candidates:      {len(report.candidates)}")
    print(f"Output:          {output_path}")
    print("Review status:   candidate")
    print()
    for candidate in report.candidates:
        sample = candidate.sample
        print(
            f"- {sample.source_name} coefficient {sample.coefficient_number}: "
            f"activation={sample.activation_time_seconds:g}s "
            f"unique_ticks={len(sample.observed_tick_times_seconds)} "
            f"raw_heal_events={candidate.raw_periodic_heal_event_count} "
            f"observed_ability_id={candidate.observed_ability_game_id}"
        )
    if report.unresolved:
        print()
        print("UNRESOLVED / SKIPPED")
        print("--------------------")
        for item in report.unresolved:
            print(f"- {item}")
    print()
    print(
        "Boundary: this output is candidate evidence only. Inspect the event pairing, "
        "then promote only explicitly approved samples with "
        "tools/review_phase13_healer_runtime_observations.py. Do not edit review_status "
        "in the candidate fixture by hand."
    )
    return 0 if report.candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
