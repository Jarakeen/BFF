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


def _next_recipient_tick(*, last_tick: float, cadence: float, after: float) -> float:
    value = float(last_tick) + float(cadence)
    while value <= after:
        value += float(cadence)
    return value


def _nearest_delta(values: tuple[float, ...], expected: float) -> float | None:
    if not values:
        return None
    return min(abs(value - expected) for value in values)


def _recipient_shape(
    *,
    post_ticks: tuple[float, ...],
    restart_first: float,
    old_next: float,
    tolerance: float,
) -> tuple[str, float | None, float | None]:
    restart_delta = _nearest_delta(post_ticks, restart_first)
    old_delta = _nearest_delta(post_ticks, old_next)
    if restart_delta is None:
        return "no-post-recast-evidence", restart_delta, old_delta
    if abs(old_next - restart_first) <= tolerance:
        return "phase-ambiguous", restart_delta, old_delta

    restart_seen = restart_delta <= tolerance
    old_seen = old_delta is not None and old_delta <= tolerance
    if restart_seen and old_seen:
        return "both-phases-observed", restart_delta, old_delta
    if restart_seen:
        return "reapplied-restart-shaped", restart_delta, old_delta
    if old_seen:
        return "old-phase-only", restart_delta, old_delta
    return "timing-unresolved", restart_delta, old_delta


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.3f}s"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect overlapping healer HoT recasts in raw ESO Logs against reviewed "
            "single-application timing. Evidence is evaluated per recipient so old ticks on "
            "one ally cannot be mistaken for failed refresh of another. This audit is read-only."
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
        help="observational timing tolerance used only for recipient phase annotations",
    )
    parser.add_argument(
        "--recipient-merge-tolerance",
        type=float,
        default=0.05,
        help="collapse near-simultaneous same-recipient heal events into one logical tick",
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

    print("=" * 84)
    print(" PHASE 13 HEALER RECIPIENT-AWARE RECAST / REFRESH CANDIDATE AUDIT")
    print("=" * 84)
    print(f"Raw export:          {args.raw}")
    print(f"Report:              {args.report_code}")
    print(f"Fight ids:           {', '.join(str(value) for value in args.fight_id)}")
    print(f"Caster sourceID:     {args.caster_id}")
    print(f"Reviewed timing:     {args.reviewed_observations}")
    print(f"Timing tolerance:    {tolerance:g}s")
    print("Boundary:            read-only recipient-level evidence; no refresh policy is promoted")

    total_overlap_pairs = 0
    total_clean_pairs = 0
    total_recipient_rows = 0
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

        pair_rows: list[tuple[int, float, float, list[tuple[int, float, float, tuple[float, ...], str, float | None, float | None]]]] = []
        skipped_prior_overlap = 0
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
                total_overlap_pairs += 1

                if index > 0:
                    prior_time = activations[index - 1][1].timestamp * scale
                    if previous_time - prior_time < duration - tolerance:
                        skipped_prior_overlap += 1
                        continue

                next_recast_time = (
                    activations[index + 2][1].timestamp * scale
                    if index + 2 < len(activations)
                    else math.inf
                )
                inspect_end = min(recast_time + duration, next_recast_time)
                old_natural_end = previous_time + duration

                by_recipient_pre: dict[int, list[float]] = {}
                by_recipient_post: dict[int, list[float]] = {}
                for event in events:
                    if (
                        event.event_kind != SemanticEventKind.HEAL
                        or event.source_id != int(args.caster_id)
                        or event.ability_game_id not in effect_ids
                        or not (event.tick is True or event.raw_event_type == "hot")
                        or event.target_id is None
                    ):
                        continue
                    event_time = event.timestamp * scale
                    recipient = int(event.target_id)
                    if previous_time <= event_time < recast_time:
                        by_recipient_pre.setdefault(recipient, []).append(event_time)
                    elif recast_time <= event_time <= inspect_end:
                        by_recipient_post.setdefault(recipient, []).append(event_time)

                recipient_rows = []
                restart_first = recast_time + first_offset
                for recipient in sorted(set(by_recipient_pre) & set(by_recipient_post)):
                    pre_ticks = extractor._collapse_recipient_tick_times(
                        by_recipient_pre[recipient],
                        merge_tolerance_seconds=merge_tolerance,
                    )
                    post_ticks = extractor._collapse_recipient_tick_times(
                        by_recipient_post[recipient],
                        merge_tolerance_seconds=merge_tolerance,
                    )
                    if not pre_ticks or not post_ticks:
                        continue
                    old_next = _next_recipient_tick(
                        last_tick=pre_ticks[-1],
                        cadence=cadence,
                        after=recast_time,
                    )
                    if old_next > old_natural_end + tolerance:
                        continue
                    shape, restart_delta, old_delta = _recipient_shape(
                        post_ticks=post_ticks,
                        restart_first=restart_first,
                        old_next=old_next,
                        tolerance=tolerance,
                    )
                    recipient_rows.append(
                        (
                            recipient,
                            pre_ticks[-1],
                            old_next,
                            post_ticks,
                            shape,
                            restart_delta,
                            old_delta,
                        )
                    )

                pair_rows.append((int(fight_id), previous_time, recast_time, recipient_rows))
                total_clean_pairs += 1
                total_recipient_rows += len(recipient_rows)

        print(f"\n{target.source_name} coefficient {target.coefficient_number}")
        print(
            f"  canonical: duration={duration:g}s cadence={cadence:g}s "
            f"reviewed_first_tick=+{first_offset:g}s"
        )
        print(f"  clean first-overlap recast pairs: {len(pair_rows)}")
        print(f"  pairs skipped because previous cast already overlapped an older cast: {skipped_prior_overlap}")
        if not pair_rows:
            print("  recipient evidence: none in selected fights")
            continue

        counts: dict[str, int] = {}
        for row_index, (fight_id, previous_time, recast_time, recipient_rows) in enumerate(pair_rows, start=1):
            print(
                f"  [{row_index:2d}] fight={fight_id} cast_gap={recast_time - previous_time:.3f}s "
                f"comparable_recipients={len(recipient_rows)}"
            )
            if not recipient_rows:
                print("       no recipient had attributable pre-recast and post-recast ticks")
                continue
            for recipient, last_pre, old_next, post_ticks, shape, restart_delta, old_delta in recipient_rows:
                counts[shape] = counts.get(shape, 0) + 1
                offsets = tuple(value - recast_time for value in post_ticks[:4])
                rendered_offsets = ", ".join(f"+{value:.3f}" for value in offsets) or "none"
                print(
                    f"       target={recipient} last_pre={last_pre - recast_time:+.3f}s "
                    f"post={rendered_offsets}"
                )
                print(
                    f"          new_first=+{first_offset:.3f}s delta={_fmt(restart_delta)} | "
                    f"continued_old_next=+{old_next - recast_time:.3f}s delta={_fmt(old_delta)} "
                    f"| shape={shape}"
                )

        if counts:
            print("  recipient-level shape counts:")
            for shape in (
                "reapplied-restart-shaped",
                "both-phases-observed",
                "old-phase-only",
                "phase-ambiguous",
                "timing-unresolved",
                "no-post-recast-evidence",
            ):
                if counts.get(shape):
                    print(f"    - {shape}: {counts[shape]}")

    print("\nInterpretation:")
    print(
        "Recipient evidence is only compared when the previous cast was not itself already "
        "overlapping an older same-skill cast and the same target has attributable ticks both "
        "before and after the recast."
    )
    print(
        "reapplied-restart-shaped means that recipient shows the reviewed new-application phase "
        "and not the projected continuation of its own old phase. both-phases-observed is evidence "
        "that two timing phases coexist on the same recipient and must not be modeled as simple restart."
    )
    print(
        "old-phase-only is not evidence against restart because the recast may not have reapplied "
        "the effect to that recipient. phase-ambiguous means the two expected phases are too close "
        "to distinguish. No row promotes a refresh policy automatically."
    )
    print(f"Overlapping recast pairs encountered: {total_overlap_pairs}")
    print(f"Clean first-overlap pairs inspected: {total_clean_pairs}")
    print(f"Comparable recipient rows inspected: {total_recipient_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
