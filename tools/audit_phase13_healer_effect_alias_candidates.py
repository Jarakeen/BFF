from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter
from services.rotation_healer_esologs_observation_extractor import (
    DF_HEALER_U50_OBSERVATION_TARGETS,
    RotationHealerEsoLogsObservationExtractor,
    RotationHealerEsoLogsTimestampUnit,
)


@dataclass(frozen=True)
class EffectAliasCandidate:
    ability_game_id: int
    windows_seen: int
    total_events: int
    tick_events: int
    first_offset_seconds: float
    last_offset_seconds: float


def _candidate_rows(
    events,
    *,
    activations,
    duration_seconds: float,
    caster_id: int,
    scale: float,
) -> tuple[EffectAliasCandidate, ...]:
    per_id: dict[int, dict[str, object]] = defaultdict(
        lambda: {
            "windows": set(),
            "events": 0,
            "ticks": 0,
            "first": None,
            "last": None,
        }
    )

    for window_index, (activation_event_index, activation) in enumerate(activations):
        start = float(activation.timestamp) * scale
        end = start + float(duration_seconds)
        for next_event_index, next_activation in activations:
            if next_event_index > activation_event_index:
                end = min(end, float(next_activation.timestamp) * scale)
                break

        for event in events:
            if event.event_kind is not SemanticEventKind.HEAL:
                continue
            if event.source_id != int(caster_id) or event.ability_game_id is None:
                continue
            event_seconds = float(event.timestamp) * scale
            if event_seconds < start or event_seconds > end:
                continue

            ability_id = int(event.ability_game_id)
            offset = event_seconds - start
            row = per_id[ability_id]
            row["windows"].add(window_index)
            row["events"] = int(row["events"]) + 1
            if event.tick is True or event.raw_event_type == "hot":
                row["ticks"] = int(row["ticks"]) + 1
            first = row["first"]
            last = row["last"]
            row["first"] = offset if first is None else min(float(first), offset)
            row["last"] = offset if last is None else max(float(last), offset)

    result = [
        EffectAliasCandidate(
            ability_game_id=ability_id,
            windows_seen=len(values["windows"]),
            total_events=int(values["events"]),
            tick_events=int(values["ticks"]),
            first_offset_seconds=round(float(values["first"]), 6),
            last_offset_seconds=round(float(values["last"]), 6),
        )
        for ability_id, values in per_id.items()
        if values["first"] is not None and values["last"] is not None
    ]
    return tuple(
        sorted(
            result,
            key=lambda item: (
                -item.windows_seen,
                -item.tick_events,
                -item.total_events,
                item.first_offset_seconds,
                item.ability_game_id,
            ),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit of candidate ESO Logs healing-effect IDs associated with "
            "known canonical healer HoT casts. Output is observational evidence only."
        )
    )
    parser.add_argument("--raw", required=True)
    parser.add_argument("--report-code", default=None)
    parser.add_argument("--fight-id", required=True, type=int)
    parser.add_argument("--caster-id", required=True, type=int)
    parser.add_argument("--db", default="data/eso.db")
    parser.add_argument(
        "--timestamp-unit",
        choices=[item.value for item in RotationHealerEsoLogsTimestampUnit],
        default=RotationHealerEsoLogsTimestampUnit.MILLISECONDS.value,
    )
    parser.add_argument("--top", type=int, default=12)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    unit = RotationHealerEsoLogsTimestampUnit(args.timestamp_unit)
    scale = unit.seconds_scale

    extractor = RotationHealerEsoLogsObservationExtractor(Path(args.db))
    fight = extractor.load_fight(
        Path(args.raw),
        fight_id=args.fight_id,
        report_code=args.report_code,
    )
    events = tuple(EsoLogsJsonEventInterpreter(fight).iter_events())

    print("================================================================")
    print(" PHASE 13 HEALER CAST -> EFFECT ALIAS CANDIDATE AUDIT")
    print("================================================================")
    print(f"Raw export:     {args.raw}")
    print(f"Report / fight: {fight.report_code} / {fight.fight_id}")
    print(f"Caster sourceID: {args.caster_id}")
    print("Boundary:       read-only observational candidates; no alias is promoted")
    print()

    any_casts = False
    for target in DF_HEALER_U50_OBSERVATION_TARGETS:
        timing = extractor.canonical_timing.resolve(
            source_name=target.source_name,
            coefficient_number=target.coefficient_number,
        )
        ability_ids = extractor.ability_ids_for_target(target)
        activations = extractor._activation_events(
            events,
            caster_id=args.caster_id,
            ability_game_ids=ability_ids,
        )

        print(f"{target.source_name} [{target.canonical_skill_id}]")
        print(f"  known cast aliases: {', '.join(map(str, ability_ids))}")
        print(f"  observed casts:     {len(activations)}")

        if not activations:
            print("  candidates:         none (no matching canonical cast in this fight)")
            print()
            continue
        any_casts = True

        if timing.duration_seconds is None:
            details = "; ".join(timing.unresolved) or "canonical duration unresolved"
            print(f"  candidates:         unavailable ({details})")
            print()
            continue

        rows = _candidate_rows(
            events,
            activations=activations,
            duration_seconds=timing.duration_seconds,
            caster_id=args.caster_id,
            scale=scale,
        )
        if not rows:
            print("  candidates:         none")
            print()
            continue

        print("  healing IDs inside cast windows:")
        for row in rows[: max(1, args.top)]:
            print(
                f"    - abilityID={row.ability_game_id} | windows={row.windows_seen}/{len(activations)} "
                f"| events={row.total_events} | tick_events={row.tick_events} "
                f"| first_offset={row.first_offset_seconds:g}s "
                f"| last_offset={row.last_offset_seconds:g}s"
            )
        print()

    print(
        "Interpretation: repeated appearance inside a skill's active windows is evidence "
        "for review, not proof of parentage. Concurrent HoTs can contaminate a window. "
        "Promote a child/effect alias only after cross-checking timing and repeated casts."
    )
    return 0 if any_casts else 1


if __name__ == "__main__":
    raise SystemExit(main())
