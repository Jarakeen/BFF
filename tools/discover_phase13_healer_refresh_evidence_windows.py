from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
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
    RotationHealerEsoLogsObservationTarget,
    RotationHealerEsoLogsTimestampUnit,
)
from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)
from tools.audit_phase13_healer_recast_observation_candidates import (
    _next_recipient_tick,
    _phase_distance,
    _recipient_shape,
)


@dataclass(frozen=True)
class RefreshEvidenceWindow:
    source_name: str
    coefficient_number: int
    report_code: str
    fight_id: int
    caster_id: int
    previous_time: float
    recast_time: float
    recipient_id: int
    phase_separation_seconds: float
    shape: str
    restart_delta_seconds: float | None
    old_delta_seconds: float | None
    post_tick_offsets_seconds: tuple[float, ...]

    @property
    def score(self) -> tuple[int, float, float, str, int, int]:
        shape_rank = {
            "reapplied-restart-shaped": 0,
            "both-phases-observed": 1,
            "old-phase-only": 2,
            "timing-unresolved": 3,
            "phase-ambiguous": 4,
            "no-post-recast-evidence": 5,
        }.get(self.shape, 9)
        restart_delta = (
            float(self.restart_delta_seconds)
            if self.restart_delta_seconds is not None
            else math.inf
        )
        return (
            shape_rank,
            -float(self.phase_separation_seconds),
            restart_delta,
            self.report_code,
            int(self.fight_id),
            int(self.recipient_id),
        )


def _target_map() -> dict[str, RotationHealerEsoLogsObservationTarget]:
    return {
        target.source_name.casefold(): target
        for target in DF_HEALER_U50_OBSERVATION_TARGETS
    }


def _corpus_fights(raw_path: Path) -> tuple[tuple[str, int], ...]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    reports = payload.get("reports") if isinstance(payload, dict) else None
    if not isinstance(reports, dict):
        report_code = str(payload.get("report_code") or "").strip()
        fights = payload.get("fights") if isinstance(payload, dict) else None
        if not isinstance(fights, dict):
            return ()
        return tuple(
            (report_code, int(fight_id))
            for fight_id in sorted(fights, key=lambda value: int(value))
        )

    rows: list[tuple[str, int]] = []
    for report_code in sorted(str(value) for value in reports):
        report_payload = reports.get(report_code)
        fights = report_payload.get("fights") if isinstance(report_payload, dict) else None
        if not isinstance(fights, dict):
            continue
        rows.extend(
            (report_code, int(fight_id))
            for fight_id in sorted(fights, key=lambda value: int(value))
        )
    return tuple(rows)


def _candidate_casters(events, *, cast_ids: tuple[int, ...]) -> tuple[int, ...]:
    aliases = {int(value) for value in cast_ids}
    return tuple(
        sorted(
            {
                int(event.source_id)
                for event in events
                if event.source_id is not None
                and event.source_is_friendly is True
                and event.ability_game_id in aliases
                and event.event_kind.value in {"cast", "completecast"}
            }
        )
    )


def _discover_for_target(
    *,
    extractor: RotationHealerEsoLogsObservationExtractor,
    raw_path: Path,
    fights: tuple[tuple[str, int], ...],
    target: RotationHealerEsoLogsObservationTarget,
    first_offset: float,
    game_version: str,
    timestamp_unit: RotationHealerEsoLogsTimestampUnit,
    timing_tolerance: float,
    recipient_merge_tolerance: float,
) -> tuple[RefreshEvidenceWindow, ...]:
    canonical = extractor.canonical_timing.resolve(
        source_name=target.source_name,
        coefficient_number=target.coefficient_number,
    )
    if not canonical.timing_ready_for_runtime_binding:
        return ()
    assert canonical.duration_seconds is not None
    assert canonical.cadence_seconds is not None
    duration = float(canonical.duration_seconds)
    cadence = float(canonical.cadence_seconds)
    scale = timestamp_unit.seconds_scale
    cast_ids = extractor.ability_ids_for_target(target)
    effect_ids = extractor.periodic_effect_ids_for_target(
        target,
        game_version=game_version,
    )

    discovered: list[RefreshEvidenceWindow] = []
    for report_code, fight_id in fights:
        fight = extractor.load_fight(
            raw_path,
            fight_id=fight_id,
            report_code=report_code or None,
        )
        events = list(EsoLogsJsonEventInterpreter(fight).iter_events())
        for caster_id in _candidate_casters(events, cast_ids=cast_ids):
            activations = extractor._activation_events(
                events,
                caster_id=caster_id,
                ability_game_ids=cast_ids,
            )
            for index in range(len(activations) - 1):
                previous_time = activations[index][1].timestamp * scale
                recast_time = activations[index + 1][1].timestamp * scale
                if recast_time - previous_time >= duration:
                    continue
                if index > 0:
                    prior_time = activations[index - 1][1].timestamp * scale
                    if previous_time - prior_time < duration - timing_tolerance:
                        continue

                next_recast_time = (
                    activations[index + 2][1].timestamp * scale
                    if index + 2 < len(activations)
                    else math.inf
                )
                inspect_end = min(recast_time + duration, next_recast_time)
                old_natural_end = previous_time + duration
                restart_first = recast_time + first_offset

                pre_by_recipient: dict[int, list[float]] = {}
                post_by_recipient: dict[int, list[float]] = {}
                for event in events:
                    if (
                        event.event_kind != SemanticEventKind.HEAL
                        or event.source_id != caster_id
                        or event.ability_game_id not in effect_ids
                        or not (event.tick is True or event.raw_event_type == "hot")
                        or event.target_id is None
                    ):
                        continue
                    event_time = event.timestamp * scale
                    recipient = int(event.target_id)
                    if previous_time <= event_time < recast_time:
                        pre_by_recipient.setdefault(recipient, []).append(event_time)
                    elif recast_time <= event_time <= inspect_end:
                        post_by_recipient.setdefault(recipient, []).append(event_time)

                for recipient_id in sorted(set(pre_by_recipient) & set(post_by_recipient)):
                    pre_ticks = extractor._collapse_recipient_tick_times(
                        pre_by_recipient[recipient_id],
                        merge_tolerance_seconds=recipient_merge_tolerance,
                    )
                    post_ticks = extractor._collapse_recipient_tick_times(
                        post_by_recipient[recipient_id],
                        merge_tolerance_seconds=recipient_merge_tolerance,
                    )
                    if not pre_ticks or not post_ticks:
                        continue
                    old_next = _next_recipient_tick(
                        last_tick=pre_ticks[-1],
                        cadence=cadence,
                        after=recast_time,
                    )
                    if old_next > old_natural_end + timing_tolerance:
                        continue
                    separation = _phase_distance(
                        first=old_next,
                        second=restart_first,
                        cadence=cadence,
                    )
                    shape, restart_delta, old_delta = _recipient_shape(
                        post_ticks=post_ticks,
                        restart_first=restart_first,
                        old_next=old_next,
                        cadence=cadence,
                        tolerance=timing_tolerance,
                    )
                    discovered.append(
                        RefreshEvidenceWindow(
                            source_name=target.source_name,
                            coefficient_number=target.coefficient_number,
                            report_code=report_code,
                            fight_id=fight_id,
                            caster_id=caster_id,
                            previous_time=previous_time,
                            recast_time=recast_time,
                            recipient_id=recipient_id,
                            phase_separation_seconds=separation,
                            shape=shape,
                            restart_delta_seconds=restart_delta,
                            old_delta_seconds=old_delta,
                            post_tick_offsets_seconds=tuple(
                                round(value - recast_time, 6)
                                for value in post_ticks[:6]
                            ),
                        )
                    )
    return tuple(sorted(discovered, key=lambda row: row.score))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Search an ESO Logs research corpus for the most useful recipient-level healer HoT "
            "recast windows. This is read-only discovery: no refresh policy is promoted."
        )
    )
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--reviewed-observations", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--skill",
        action="append",
        default=["Budding Seeds", "Radiating Regeneration"],
        help="tracked healer skill to search; repeat for multiple skills",
    )
    parser.add_argument("--game-version", default="U50")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--timing-tolerance", type=float, default=0.1)
    parser.add_argument("--recipient-merge-tolerance", type=float, default=0.05)
    parser.add_argument(
        "--timestamp-unit",
        choices=tuple(item.value for item in RotationHealerEsoLogsTimestampUnit),
        default=RotationHealerEsoLogsTimestampUnit.MILLISECONDS.value,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if int(args.top) <= 0:
        raise ValueError("--top must be positive")
    if float(args.timing_tolerance) < 0 or float(args.recipient_merge_tolerance) < 0:
        raise ValueError("timing tolerances must be non-negative")

    targets = _target_map()
    requested: list[RotationHealerEsoLogsObservationTarget] = []
    for name in args.skill:
        target = targets.get(str(name).strip().casefold())
        if target is None:
            available = ", ".join(sorted(item.source_name for item in targets.values()))
            raise ValueError(f"unknown tracked healer skill {name!r}; available: {available}")
        if target not in requested:
            requested.append(target)

    extractor = RotationHealerEsoLogsObservationExtractor(args.db)
    fixture = RotationHealerPeriodicObservationFixtureService(args.db).load(
        args.reviewed_observations
    )
    observations = {
        (item.source_name.casefold(), int(item.coefficient_number), item.game_version): item
        for item in fixture.reviewed_observations
    }
    fights = _corpus_fights(args.raw)
    timestamp_unit = RotationHealerEsoLogsTimestampUnit(args.timestamp_unit)

    print("=" * 92)
    print(" PHASE 13 HEALER REFRESH EVIDENCE WINDOW DISCOVERY")
    print("=" * 92)
    print(f"Raw corpus:       {args.raw}")
    print(f"Reports/fights:   {len(fights)}")
    print(f"Reviewed timing:  {args.reviewed_observations}")
    print("Boundary:         read-only discovery; candidate windows are not reviewed policy evidence")

    any_rows = False
    for target in requested:
        observation = observations.get(
            (target.source_name.casefold(), int(target.coefficient_number), str(args.game_version))
        )
        if observation is None or observation.first_tick_offset_seconds is None:
            print(f"\n{target.source_name} coefficient {target.coefficient_number}: reviewed first tick unavailable")
            continue
        rows = _discover_for_target(
            extractor=extractor,
            raw_path=args.raw,
            fights=fights,
            target=target,
            first_offset=float(observation.first_tick_offset_seconds),
            game_version=str(args.game_version),
            timestamp_unit=timestamp_unit,
            timing_tolerance=float(args.timing_tolerance),
            recipient_merge_tolerance=float(args.recipient_merge_tolerance),
        )
        any_rows = any_rows or bool(rows)
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.shape] = counts.get(row.shape, 0) + 1

        print(f"\n{target.source_name} coefficient {target.coefficient_number}")
        print(f"  comparable recipient windows found: {len(rows)}")
        if counts:
            print("  shape counts: " + ", ".join(f"{key}={counts[key]}" for key in sorted(counts)))
        if not rows:
            print("  no usable recipient-level recast windows found anywhere in this corpus")
            continue

        print(f"  top {min(int(args.top), len(rows))} evidence windows:")
        for index, row in enumerate(rows[: int(args.top)], start=1):
            offsets = ", ".join(f"+{value:.3f}" for value in row.post_tick_offsets_seconds)
            print(
                f"    [{index:2d}] {row.shape:24s} report={row.report_code} fight={row.fight_id} "
                f"caster={row.caster_id} target={row.recipient_id} cast_gap={row.recast_time - row.previous_time:.3f}s "
                f"phase_sep={row.phase_separation_seconds:.3f}s"
            )
            print(
                f"         recast={row.recast_time:.3f}s post={offsets or 'none'} "
                f"restart_delta={row.restart_delta_seconds if row.restart_delta_seconds is not None else 'n/a'} "
                f"old_delta={row.old_delta_seconds if row.old_delta_seconds is not None else 'n/a'}"
            )

    print("\nInterpretation:")
    print(
        "Prefer windows with large phase separation and reapplied-restart-shaped same-recipient "
        "evidence. phase-ambiguous windows are poor review candidates even when numerous."
    )
    print(
        "Use the printed report/fight/caster tuple with the recipient-aware recast audit for "
        "human review before adding or changing any reviewed refresh policy."
    )
    return 0 if any_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
