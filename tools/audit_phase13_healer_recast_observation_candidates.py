from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter
from services.rotation_healer_esologs_observation_extractor import (
    DF_HEALER_U50_OBSERVATION_TARGETS,
    RotationHealerEsoLogsObservationExtractor,
    RotationHealerEsoLogsTimestampUnit,
)
from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)


def _next_phase_time(*, origin: float, first_offset: float, cadence: float, after: float) -> float:
    first = origin + first_offset
    if first > after:
        return first
    steps = math.floor((after - first) / cadence) + 1
    return first + steps * cadence


def _nearest_delta(values: tuple[float, ...], expected: float) -> float | None:
    if not values:
        return None
    return min(abs(value - expected) for value in values)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.3f}s"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect overlapping healer HoT recasts in raw ESO Logs against reviewed "
            "single-application timing. This audit is read-only and does not promote a refresh policy."
        )
    )
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--report-code", required=True)
    parser.add_argument("--fight-id", type=int, action="append", required=True)
    parser.add_argument("--caster-id", type=int, required=True)
    parser.add_argument("--reviewed-observations", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--game-version", default="U50")
    parser.add_argument(
        "--timestamp-unit",
        choices=tuple(item.value for item in RotationHealerEsoLogsTimestampUnit),
        default=RotationHealerEsoLogsTimestampUnit.MILLISECONDS.value,
    )
    parser.add_argument(
        "--timing-tolerance",
        type=float,
        default=0.1,
        help="observational timing tolerance used only for restart-shape annotations",
    )
    parser.add_argument(
        "--recipient-merge-tolerance",
        type=float,
        default=0.05,
        help="collapse near-simultaneous recipient heal events into one logical tick",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tolerance = float(args.timing_tolerance)
    merge_tolerance = float(args.recipient_merge_tolerance)
    if tolerance < 0 or merge_tolerance < 0:
        raise ValueError("timing tolerances must be non-negative")

    extractor = RotationHealerEsoLogsObservationExtractor(args.db)
    fixture = RotationHealerPeriodicObservationFixtureService(args.db).load(
        args.reviewed_observations
    )
    observations = {
        (
            item.source_name.casefold(),
            int(item.coefficient_number),
            item.game_version,
        ): item
        for item in fixture.reviewed_observations
    }

    unit = RotationHealerEsoLogsTimestampUnit(args.timestamp_unit)
    scale = unit.seconds_scale

    print("=" * 76)
    print(" PHASE 13 HEALER RECAST / REFRESH OBSERVATION CANDIDATE AUDIT")
    print("=" * 76)
    print(f"Raw export:          {args.raw}")
    print(f"Report:              {args.report_code}")
    print(f"Fight ids:           {', '.join(str(value) for value in args.fight_id)}")
    print(f"Caster sourceID:     {args.caster_id}")
    print(f"Reviewed timing:     {args.reviewed_observations}")
    print(f"Timing tolerance:    {tolerance:g}s")
    print("Boundary:            read-only observational evidence; no refresh policy is promoted")

    total_overlap_pairs = 0
    for target in DF_HEALER_U50_OBSERVATION_TARGETS:
        canonical = extractor.canonical_timing.resolve(
            source_name=target.source_name,
            coefficient_number=target.coefficient_number,
        )
        if not canonical.timing_ready_for_runtime_binding:
            print(f"\n{target.source_name} coefficient {target.coefficient_number}: canonical timing unresolved")
            continue

        observation = observations.get(
            (
                target.source_name.casefold(),
                int(target.coefficient_number),
                str(args.game_version),
            )
        )
        if observation is None or observation.first_tick_offset_seconds is None:
            print(
                f"\n{target.source_name} coefficient {target.coefficient_number}: "
                "reviewed first-tick consensus unavailable"
            )
            continue

        assert canonical.duration_seconds is not None
        assert canonical.cadence_seconds is not None
        duration = float(canonical.duration_seconds)
        cadence = float(canonical.cadence_seconds)
        first_offset = float(observation.first_tick_offset_seconds)
        cast_ids = extractor.ability_ids_for_target(target)
        effect_ids = extractor.periodic_effect_ids_for_target(
            target,
            game_version=str(args.game_version),
        )

        rows: list[tuple[int, float, float, tuple[float, ...], float, float, float | None, float | None, bool | None]] = []
        for fight_id in args.fight_id:
            fight = extractor.load_fight(
                args.raw,
                fight_id=int(fight_id),
                report_code=args.report_code,
            )
            events = list(EsoLogsJsonEventInterpreter(fight).iter_events())
            activations = extractor._activation_events(
                events,
                caster_id=int(args.caster_id),
                ability_game_ids=cast_ids,
            )
            for index in range(len(activations) - 1):
                _, previous = activations[index]
                _, recast = activations[index + 1]
                previous_time = previous.timestamp * scale
                recast_time = recast.timestamp * scale
                cast_gap = recast_time - previous_time
                if cast_gap >= duration:
                    continue

                next_recast_time = (
                    activations[index + 2][1].timestamp * scale
                    if index + 2 < len(activations)
                    else math.inf
                )
                inspect_end = min(recast_time + duration, next_recast_time)
                raw_post = [
                    event.timestamp * scale
                    for event in events
                    if event.event_kind == SemanticEventKind.HEAL
                    and event.source_id == int(args.caster_id)
                    and event.ability_game_id in effect_ids
                    and (event.tick is True or event.raw_event_type == "hot")
                    and recast_time <= event.timestamp * scale <= inspect_end
                ]
                post_ticks = extractor._collapse_recipient_tick_times(
                    raw_post,
                    merge_tolerance_seconds=merge_tolerance,
                )
                restart_first = recast_time + first_offset
                old_next = _next_phase_time(
                    origin=previous_time,
                    first_offset=first_offset,
                    cadence=cadence,
                    after=recast_time,
                )
                restart_delta = _nearest_delta(post_ticks, restart_first)
                old_delta = _nearest_delta(post_ticks, old_next)
                restart_shape: bool | None
                if restart_delta is None:
                    restart_shape = None
                elif abs(old_next - restart_first) <= tolerance:
                    restart_shape = None
                else:
                    restart_shape = restart_delta <= tolerance and (
                        old_delta is None or old_delta > tolerance
                    )
                rows.append(
                    (
                        int(fight_id),
                        previous_time,
                        recast_time,
                        post_ticks,
                        restart_first,
                        old_next,
                        restart_delta,
                        old_delta,
                        restart_shape,
                    )
                )

        print(f"\n{target.source_name} coefficient {target.coefficient_number}")
        print(
            f"  canonical: duration={duration:g}s cadence={cadence:g}s "
            f"reviewed_first_tick=+{first_offset:g}s"
        )
        print(f"  overlapping recast pairs: {len(rows)}")
        total_overlap_pairs += len(rows)
        if not rows:
            print("  evidence: none in selected fights")
            continue

        for row_index, row in enumerate(rows, start=1):
            (
                fight_id,
                previous_time,
                recast_time,
                post_ticks,
                restart_first,
                old_next,
                restart_delta,
                old_delta,
                restart_shape,
            ) = row
            offsets = tuple(value - recast_time for value in post_ticks[:5])
            rendered_offsets = ", ".join(f"+{value:.3f}" for value in offsets) or "none"
            if restart_shape is True:
                shape = "restart-shaped candidate"
            elif restart_shape is False:
                shape = "not restart-shaped"
            else:
                shape = "timing-ambiguous"
            print(
                f"  [{row_index:2d}] fight={fight_id} cast_gap={recast_time - previous_time:.3f}s "
                f"post_ticks={rendered_offsets}"
            )
            print(
                f"       expected_new_first=+{restart_first - recast_time:.3f}s "
                f"nearest_delta={_fmt(restart_delta)} | "
                f"old_stream_next=+{old_next - recast_time:.3f}s nearest_delta={_fmt(old_delta)}"
            )
            print(f"       shape={shape}")

    print("\nInterpretation:")
    print(
        "A restart-shaped candidate means the observed post-recast stream matches the reviewed "
        "new-application phase while a distinct old-stream phase is absent inside the selected tolerance."
    )
    print(
        "Timing-ambiguous rows are not evidence against restart; they occur when the old and new "
        "phases are too close to distinguish or when insufficient post-recast ticks are visible."
    )
    print(
        "This audit does not promote RESTART. Cross-fight agreement must be reviewed explicitly before "
        "refresh/recast semantics enter runtime evidence."
    )
    print(f"Total overlapping recast pairs inspected: {total_overlap_pairs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
