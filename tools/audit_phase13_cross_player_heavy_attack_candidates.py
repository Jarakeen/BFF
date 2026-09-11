from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter, EsoLogsJsonFight


PLAUSIBLE_ACTION_TYPES = frozenset({"begincast", "cast", "damage", "calculateddamage"})
DEFAULT_SEED_RESTORE_IDS = (95042, 94973)


def _iter_corpus_fights(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise ValueError(f"{path}: expected payload['reports'] to be an object")
    for report_code, report_row in reports.items():
        if not isinstance(report_row, dict):
            continue
        fights = report_row.get("fights")
        if not isinstance(fights, dict):
            continue
        for fight_key, fight_row in fights.items():
            if not isinstance(fight_row, dict):
                continue
            try:
                fight_id = int(fight_key)
            except (TypeError, ValueError):
                continue
            single_payload = {
                "report_code": str(report_code),
                "fights": {str(fight_id): fight_row},
            }
            fight = EsoLogsJsonFight.from_payload(
                single_payload,
                fight_id=fight_id,
                report_code=str(report_code),
                source_name=str(path),
            )
            yield fight


def _nearest_preceding_action(events, *, source_id: int, timestamp: float, lookback_ms: float):
    best = None
    best_delta = None
    for event in events:
        if event.source_id != source_id:
            continue
        if event.raw_event_type not in PLAUSIBLE_ACTION_TYPES:
            continue
        delta = float(timestamp) - float(event.timestamp)
        if delta < 0.0 or delta > lookback_ms:
            continue
        if best_delta is None or delta < best_delta:
            best = event
            best_delta = delta
    return best, best_delta


def _seed_signatures(
    fights,
    *,
    seed_source_id: int,
    seed_report_code: str | None,
    seed_restore_ids: tuple[int, ...],
    seed_restore_amount: float,
    lookback_ms: float,
):
    signatures = []
    seeds = []
    restore_ids = set(seed_restore_ids)
    for fight, events in fights:
        if seed_report_code is not None and fight.report_code != seed_report_code:
            continue
        for event in events:
            if event.event_kind != SemanticEventKind.RESOURCE_CHANGE:
                continue
            if event.source_id != seed_source_id:
                continue
            if event.ability_game_id not in restore_ids:
                continue
            if event.resource_change is None or float(event.resource_change) != float(seed_restore_amount):
                continue
            action, delta = _nearest_preceding_action(
                events,
                source_id=seed_source_id,
                timestamp=float(event.timestamp),
                lookback_ms=lookback_ms,
            )
            seeds.append((fight, event, action, delta))
            if action is not None:
                signatures.append(
                    (action.raw_event_type, action.ability_game_id, action.ability_name)
                )
    return tuple(seeds), Counter(signatures)


def _follow_resource_events(events, *, action, forward_ms: float):
    rows = []
    for event in events:
        if event.event_kind != SemanticEventKind.RESOURCE_CHANGE:
            continue
        if event.source_id != action.source_id:
            continue
        delta = float(event.timestamp) - float(action.timestamp)
        if delta < 0.0 or delta > forward_ms:
            continue
        if event.resource_change is None or float(event.resource_change) <= 0.0:
            continue
        rows.append((event, delta))
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Use reviewed heavy-restore seed events to identify a repeated preceding action signature, "
            "then scan all players in the raw Lokkestiiz corpus for the same action and associated "
            "positive resource restores. Candidate observational evidence only."
        )
    )
    parser.add_argument("--path", type=Path, default=Path("research/raw/lokkestiiz_corpus.json"))
    parser.add_argument("--seed-source-id", type=int, default=7)
    parser.add_argument("--seed-report-code", default="btZpy9j6KzYXkRL3")
    parser.add_argument("--seed-restore-id", type=int, action="append", default=[])
    parser.add_argument("--seed-restore-amount", type=float, default=3960.0)
    parser.add_argument("--lookback-ms", type=float, default=2500.0)
    parser.add_argument("--forward-ms", type=float, default=1000.0)
    parser.add_argument("--signature-rank", type=int, default=1)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    if not args.path.exists():
        raise FileNotFoundError(args.path)
    if args.lookback_ms <= 0 or args.forward_ms < 0:
        raise ValueError("lookback/forward windows must be positive")
    if args.signature_rank <= 0 or args.limit <= 0:
        raise ValueError("signature-rank and limit must be positive")

    loaded = []
    for fight in _iter_corpus_fights(args.path):
        loaded.append((fight, tuple(EsoLogsJsonEventInterpreter(fight).iter_events())))

    restore_ids = tuple(args.seed_restore_id or DEFAULT_SEED_RESTORE_IDS)
    seeds, signature_counts = _seed_signatures(
        loaded,
        seed_source_id=int(args.seed_source_id),
        seed_report_code=(None if not args.seed_report_code else str(args.seed_report_code)),
        seed_restore_ids=restore_ids,
        seed_restore_amount=float(args.seed_restore_amount),
        lookback_ms=float(args.lookback_ms),
    )

    print("=" * 112)
    print(" PHASE 13 CROSS-PLAYER FULLY-CHARGED HEAVY-ATTACK CANDIDATE AUDIT")
    print("=" * 112)
    print("Evidence status: CANDIDATE OBSERVATION ONLY")
    print(f"Raw corpus:          {args.path}")
    print(f"Seed report:         {args.seed_report_code or 'all reports'}")
    print(f"Seed source:         {args.seed_source_id}")
    print(f"Seed restore ids:    {', '.join(str(v) for v in restore_ids)}")
    print(f"Seed restore amount: {args.seed_restore_amount:g}")
    print(f"Seed events found:   {len(seeds)}")
    print()

    print("SEED EVENT → NEAREST PRECEDING ACTION")
    print("-------------------------------------")
    for fight, restore, action, delta in seeds[: args.limit]:
        if action is None:
            print(
                f"report={fight.report_code} fight={fight.fight_id} restore_event={restore.event_index} "
                "preceding_action=NONE"
            )
            continue
        print(
            f"report={fight.report_code} fight={fight.fight_id} restore_event={restore.event_index} "
            f"restore={float(restore.resource_change):g} <- {float(delta):g}ms <- "
            f"{action.raw_event_type}:{action.ability_name or '(unnamed)'} "
            f"[{action.ability_game_id}] action_event={action.event_index}"
        )

    print()
    print("RANKED PRECEDING ACTION SIGNATURES")
    print("----------------------------------")
    ranked = signature_counts.most_common()
    for index, ((raw_type, ability_id, name), count) in enumerate(ranked[: args.limit], start=1):
        print(
            f"#{index:2d} {count:3d}/{len(seeds):3d} seeds | "
            f"{raw_type}:{name or '(unnamed)'} [{ability_id}]"
        )

    if len(ranked) < args.signature_rank:
        print("\nUNRESOLVED: requested signature rank is unavailable.")
        return 3

    chosen_signature, chosen_seed_count = ranked[args.signature_rank - 1]
    chosen_type, chosen_ability_id, chosen_name = chosen_signature
    print()
    print("CROSS-PLAYER SCAN SIGNATURE")
    print("---------------------------")
    print(
        f"rank={args.signature_rank} seed_support={chosen_seed_count}/{len(seeds)} "
        f"signature={chosen_type}:{chosen_name or '(unnamed)'} [{chosen_ability_id}]"
    )

    observations = []
    action_count = 0
    distinct_sources = set()
    distinct_reports = set()
    for fight, events in loaded:
        for action in events:
            if action.raw_event_type != chosen_type:
                continue
            if action.ability_game_id != chosen_ability_id:
                continue
            if action.source_id is None:
                continue
            action_count += 1
            distinct_sources.add((fight.report_code, action.source_id))
            distinct_reports.add(fight.report_code)
            for restore, delta in _follow_resource_events(
                events,
                action=action,
                forward_ms=float(args.forward_ms),
            ):
                observations.append((fight, action, restore, delta))

    print(f"Matching actions:      {action_count}")
    print(f"Report/source actors:  {len(distinct_sources)}")
    print(f"Reports represented:   {len(distinct_reports)}")
    print(f"Positive restores:     {len(observations)}")

    by_restore = Counter(
        (float(restore.resource_change), restore.resource_change_type, restore.ability_game_id)
        for _fight, _action, restore, _delta in observations
    )
    print()
    print("CROSS-PLAYER RESTORE DISTRIBUTION")
    print("---------------------------------")
    for (amount, resource_type, restore_ability_id), count in by_restore.most_common(args.limit):
        print(
            f"{count:5d} events | restore={amount:g} | resource_type={resource_type} | "
            f"restore_ability_id={restore_ability_id}"
        )

    by_actor = defaultdict(list)
    for fight, action, restore, delta in observations:
        by_actor[(fight.report_code, fight.fight_id, int(action.source_id))].append(
            (float(restore.resource_change), restore.resource_change_type, restore.ability_game_id, delta)
        )

    print()
    print("PER-ACTOR SUMMARY")
    print("-----------------")
    for (report_code, fight_id, source_id), rows in sorted(by_actor.items())[: args.limit]:
        amounts = Counter(value[0] for value in rows)
        common = ", ".join(f"{amount:g}x{count}" for amount, count in amounts.most_common(5))
        print(
            f"report={report_code} fight={fight_id} source={source_id} "
            f"restore_events={len(rows)} common=[{common}]"
        )

    print()
    print("EVENT PROVENANCE")
    print("----------------")
    for fight, action, restore, delta in observations[: args.limit]:
        print(
            f"report={fight.report_code} fight={fight.fight_id} source={action.source_id} "
            f"action_event={action.event_index} action_time={action.timestamp:g} "
            f"restore_event={restore.event_index} +{delta:g}ms restore={float(restore.resource_change):g} "
            f"resource_type={restore.resource_change_type} restore_id={restore.ability_game_id} "
            f"waste={restore.waste} max_resource={restore.max_resource_amount}"
        )

    print()
    print("BOUNDARY")
    print("--------")
    print("- The seed restore ids/amount identify candidate evidence; they are not canonical mechanics.")
    print("- The chosen action is based on repeated temporal correlation, not raw numeric-id authority.")
    print("- Cross-player matches remain observational until the action signature is human-reviewed as a fully charged heavy.")
    print("- Restore amounts may differ with weapon/passives/armor/runtime modifiers and must retain provenance.")
    print("- This audit reads raw research JSON only and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
