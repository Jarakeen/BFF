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
    recipient_id: int
    cast_gap_seconds: float
    recast_time_seconds: float
    phase_separation_seconds: float
    shape: str
    restart_delta_seconds: float | None
    old_delta_seconds: float | None
    post_tick_offsets_seconds: tuple[float, ...]

    @property
    def score(self):
        shape_rank = {
            "reapplied-restart-shaped": 0,
            "both-phases-observed": 1,
            "old-phase-only": 2,
            "timing-unresolved": 3,
            "phase-ambiguous": 4,
        }.get(self.shape, 9)
        restart_delta = self.restart_delta_seconds if self.restart_delta_seconds is not None else math.inf
        return (
            shape_rank,
            -self.phase_separation_seconds,
            restart_delta,
            self.report_code,
            self.fight_id,
            self.recipient_id,
        )


def _corpus_fights(path: Path) -> tuple[tuple[str, int], ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    reports = payload.get("reports") if isinstance(payload, dict) else None
    if isinstance(reports, dict):
        rows = []
        for report_code in sorted(reports):
            fights = reports[report_code].get("fights", {}) if isinstance(reports[report_code], dict) else {}
            if isinstance(fights, dict):
                rows.extend((str(report_code), int(fight_id)) for fight_id in fights)
        return tuple(sorted(rows))
    fights = payload.get("fights", {}) if isinstance(payload, dict) else {}
    report_code = str(payload.get("report_code") or "") if isinstance(payload, dict) else ""
    return tuple((report_code, int(fight_id)) for fight_id in fights) if isinstance(fights, dict) else ()


def _candidate_casters(events, cast_ids: tuple[int, ...]) -> tuple[int, ...]:
    aliases = {int(value) for value in cast_ids}
    return tuple(sorted({
        int(event.source_id)
        for event in events
        if event.source_id is not None
        and event.source_is_friendly is True
        and event.ability_game_id in aliases
        and event.event_kind == SemanticEventKind.CAST
    }))


def _discover(
    *,
    extractor,
    raw_path: Path,
    fights: tuple[tuple[str, int], ...],
    target,
    first_offset: float,
    game_version: str,
    unit: RotationHealerEsoLogsTimestampUnit,
    timing_tolerance: float,
    merge_tolerance: float,
) -> tuple[RefreshEvidenceWindow, ...]:
    canonical = extractor.canonical_timing.resolve(
        source_name=target.source_name,
        coefficient_number=target.coefficient_number,
    )
    if not canonical.timing_ready_for_runtime_binding:
        return ()
    duration = float(canonical.duration_seconds)
    cadence = float(canonical.cadence_seconds)
    scale = unit.seconds_scale
    cast_ids = extractor.ability_ids_for_target(target)
    effect_ids = extractor.periodic_effect_ids_for_target(target, game_version=game_version)
    rows: list[RefreshEvidenceWindow] = []

    for report_code, fight_id in fights:
        fight = extractor.load_fight(raw_path, fight_id=fight_id, report_code=report_code or None)
        events = list(EsoLogsJsonEventInterpreter(fight).iter_events())
        for caster_id in _candidate_casters(events, cast_ids):
            activations = extractor._activation_events(events, caster_id=caster_id, ability_game_ids=cast_ids)
            for index in range(len(activations) - 1):
                previous = activations[index][1].timestamp * scale
                recast = activations[index + 1][1].timestamp * scale
                gap = recast - previous
                if gap >= duration:
                    continue
                if index > 0:
                    prior = activations[index - 1][1].timestamp * scale
                    if previous - prior < duration - timing_tolerance:
                        continue
                next_recast = activations[index + 2][1].timestamp * scale if index + 2 < len(activations) else math.inf
                inspect_end = min(recast + duration, next_recast)
                old_end = previous + duration
                pre: dict[int, list[float]] = {}
                post: dict[int, list[float]] = {}
                for event in events:
                    if (
                        event.event_kind != SemanticEventKind.HEAL
                        or event.source_id != caster_id
                        or event.ability_game_id not in effect_ids
                        or not (event.tick is True or event.raw_event_type == "hot")
                        or event.target_id is None
                    ):
                        continue
                    when = event.timestamp * scale
                    recipient = int(event.target_id)
                    if previous <= when < recast:
                        pre.setdefault(recipient, []).append(when)
                    elif recast <= when <= inspect_end:
                        post.setdefault(recipient, []).append(when)

                for recipient in sorted(set(pre) & set(post)):
                    pre_ticks = extractor._collapse_recipient_tick_times(pre[recipient], merge_tolerance_seconds=merge_tolerance)
                    post_ticks = extractor._collapse_recipient_tick_times(post[recipient], merge_tolerance_seconds=merge_tolerance)
                    if not pre_ticks or not post_ticks:
                        continue
                    old_next = _next_recipient_tick(last_tick=pre_ticks[-1], cadence=cadence, after=recast)
                    if old_next > old_end + timing_tolerance:
                        continue
                    restart_first = recast + first_offset
                    separation = _phase_distance(first=old_next, second=restart_first, cadence=cadence)
                    shape, restart_delta, old_delta = _recipient_shape(
                        post_ticks=post_ticks,
                        restart_first=restart_first,
                        old_next=old_next,
                        cadence=cadence,
                        tolerance=timing_tolerance,
                    )
                    rows.append(RefreshEvidenceWindow(
                        source_name=target.source_name,
                        coefficient_number=target.coefficient_number,
                        report_code=report_code,
                        fight_id=fight_id,
                        caster_id=caster_id,
                        recipient_id=recipient,
                        cast_gap_seconds=gap,
                        recast_time_seconds=recast,
                        phase_separation_seconds=separation,
                        shape=shape,
                        restart_delta_seconds=restart_delta,
                        old_delta_seconds=old_delta,
                        post_tick_offsets_seconds=tuple(round(value - recast, 6) for value in post_ticks[:6]),
                    ))
    return tuple(sorted(rows, key=lambda row: row.score))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover the strongest recipient-level recast evidence windows for unresolved healer HoTs. Read-only; no policy promotion.")
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--reviewed-observations", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--skill", action="append", default=None)
    parser.add_argument("--game-version", default="U50")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--timing-tolerance", type=float, default=0.1)
    parser.add_argument("--recipient-merge-tolerance", type=float, default=0.05)
    parser.add_argument("--timestamp-unit", choices=tuple(item.value for item in RotationHealerEsoLogsTimestampUnit), default=RotationHealerEsoLogsTimestampUnit.MILLISECONDS.value)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.top <= 0 or args.timing_tolerance < 0 or args.recipient_merge_tolerance < 0:
        raise ValueError("top must be positive and timing tolerances non-negative")

    targets = {target.source_name.casefold(): target for target in DF_HEALER_U50_OBSERVATION_TARGETS}
    names = args.skill or ["Budding Seeds", "Radiating Regeneration"]
    requested = []
    for name in names:
        target = targets.get(str(name).strip().casefold())
        if target is None:
            raise ValueError(f"unknown tracked healer skill: {name}")
        if target not in requested:
            requested.append(target)

    extractor = RotationHealerEsoLogsObservationExtractor(args.db)
    fixture = RotationHealerPeriodicObservationFixtureService(args.db).load(args.reviewed_observations)
    observations = {
        (item.source_name.casefold(), int(item.coefficient_number), item.game_version): item
        for item in fixture.reviewed_observations
    }
    fights = _corpus_fights(args.raw)
    unit = RotationHealerEsoLogsTimestampUnit(args.timestamp_unit)

    print("=" * 92)
    print(" PHASE 13 HEALER REFRESH EVIDENCE WINDOW DISCOVERY")
    print("=" * 92)
    print(f"Raw corpus:      {args.raw}")
    print(f"Reports/fights:  {len(fights)}")
    print("Boundary:        read-only discovery; output is not reviewed policy evidence")

    found = False
    for target in requested:
        observation = observations.get((target.source_name.casefold(), int(target.coefficient_number), str(args.game_version)))
        if observation is None or observation.first_tick_offset_seconds is None:
            print(f"\n{target.source_name}: reviewed first-tick observation unavailable")
            continue
        rows = _discover(
            extractor=extractor,
            raw_path=args.raw,
            fights=fights,
            target=target,
            first_offset=float(observation.first_tick_offset_seconds),
            game_version=str(args.game_version),
            unit=unit,
            timing_tolerance=float(args.timing_tolerance),
            merge_tolerance=float(args.recipient_merge_tolerance),
        )
        found = found or bool(rows)
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.shape] = counts.get(row.shape, 0) + 1
        print(f"\n{target.source_name} coefficient {target.coefficient_number}")
        print(f"  comparable recipient windows: {len(rows)}")
        if counts:
            print("  shapes: " + ", ".join(f"{key}={counts[key]}" for key in sorted(counts)))
        for index, row in enumerate(rows[: args.top], start=1):
            offsets = ", ".join(f"+{value:.3f}" for value in row.post_tick_offsets_seconds)
            print(
                f"  [{index:2d}] {row.shape:24s} report={row.report_code} fight={row.fight_id} caster={row.caster_id} "
                f"target={row.recipient_id} gap={row.cast_gap_seconds:.3f}s phase_sep={row.phase_separation_seconds:.3f}s"
            )
            print(
                f"       recast={row.recast_time_seconds:.3f}s post={offsets or 'none'} "
                f"restart_delta={row.restart_delta_seconds if row.restart_delta_seconds is not None else 'n/a'} "
                f"old_delta={row.old_delta_seconds if row.old_delta_seconds is not None else 'n/a'}"
            )

    print("\nPrefer large phase separation plus reapplied-restart-shaped same-recipient windows for review.")
    print("Then rerun the recipient-aware recast audit on the printed report/fight/caster tuple before promotion.")
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
