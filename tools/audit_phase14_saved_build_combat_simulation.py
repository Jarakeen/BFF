from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from models.combat_simulation import CombatSimulationCombatant, CombatSimulationTargetState
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.combat_simulation_damage_summary_service import (
    CombatSimulationDamageSummaryService,
)
from services.combat_simulation_deterministic_replay_service import (
    CombatSimulationDeterministicReplayService,
)
from services.combat_simulation_plan_attacker_state_service import (
    CombatSimulationPlanAttackerStateService,
)
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderService,
)
from services.combat_simulation_saved_build_dd_service import (
    CombatSimulationSavedBuildDDService,
)
from services.rotation_dd_relevant_static_context_service import (
    RotationDDRelevantStaticContextService,
)
from services.rotation_explicit_target_combat_state_schedule_service import (
    RotationExplicitTargetCombatStateScheduleService,
    RotationTargetCombatStateWindow,
)
from services.rotation_plan_potion_combat_state_service import (
    RotationPlanPotionCombatStateService,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextService,
)
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from tools.dd_audit_activation_anchor_support import (
    build_explicit_activation_anchor_resolver,
    parse_explicit_impact_anchor,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationSupport,
)


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _saved_dd_builds(path: Path) -> tuple[PlayerBuild, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    members = payload.get("Members", []) if isinstance(payload, dict) else []
    result: list[PlayerBuild] = []
    for raw in members:
        if not isinstance(raw, dict):
            continue
        role = " ".join(
            str(raw.get("Role", "") or "")
            .strip()
            .casefold()
            .replace("_", " ")
            .split()
        )
        if role not in _DD_ROLE_KEYS:
            continue
        result.append(PlayerBuild.from_dict(raw))
    return tuple(
        sorted(
            result,
            key=lambda build: (
                _character_name(build).casefold(),
                str(getattr(build, "BuildName", "") or "").strip().casefold(),
            ),
        )
    )


def _print_saved_dd_builds(path: Path) -> int:
    builds = _saved_dd_builds(path)
    print("=" * 76)
    print(" SAVED DD BUILDS AVAILABLE FOR PHASE 14 COMBAT SIMULATION")
    print("=" * 76)
    if not builds:
        print("none")
        return 1
    for build in builds:
        print(
            f"{_character_name(build) or '(unnamed character)'} | "
            f"{getattr(build, 'BuildName', '') or '(unnamed build)'} | "
            f"{getattr(build, 'Role', '') or 'unresolved'}"
        )
    return 0


def _parse_window(raw: str) -> RotationTargetCombatStateWindow:
    text = str(raw or "").strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Off Balance window must use START:END seconds, got {raw!r}"
        )
    return RotationTargetCombatStateWindow(
        float(parts[0]),
        float(parts[1]),
        ("Off Balance",),
    )


def _format_pct(current: int | None, maximum: int | None) -> str:
    if current is None or maximum is None or maximum <= 0:
        return "unknown"
    return f"{(float(current) / float(maximum)):.2%}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one real saved DD build through Phase 14 Combat Simulation using "
            "the generated RotationPlan and canonical damage providers."
        )
    )
    parser.add_argument("--build")
    parser.add_argument("--character")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "eso.db")
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--target-health", type=int)
    parser.add_argument("--target-resistance", type=float)
    parser.add_argument(
        "--list-dd-builds",
        action="store_true",
        help="List saved DD/DPS builds from builds.json and exit.",
    )
    parser.add_argument("--target-name", default="Boss")
    parser.add_argument(
        "--target-state-known",
        action="store_true",
        help=(
            "Treat target CombatState as authoritative. With no windows, the target "
            "is known to have no named scheduled buffs."
        ),
    )
    parser.add_argument(
        "--off-balance-window",
        action="append",
        default=[],
        metavar="START:END",
        help="Add one authoritative half-open Off Balance window [START, END).",
    )
    parser.add_argument(
        "--impact-anchor",
        action="append",
        default=[],
        metavar="SKILL:ACTION_TIME:SEQUENCE:IMPACT_TIME",
        help="Supply one reviewed non-cast periodic activation anchor.",
    )
    parser.add_argument(
        "--no-weave",
        action="store_true",
        help="Disable generated light-attack weaving.",
    )
    parser.add_argument("--ultimate-bar", choices=("front", "back"))
    parser.add_argument("--starting-ultimate", type=float, default=0.0)
    parser.add_argument(
        "--use-scheduled-attacks-for-ultimate",
        action="store_true",
    )
    parser.add_argument(
        "--show-events",
        action="store_true",
        help="Print modeled outgoing-damage and Health events.",
    )
    args = parser.parse_args()

    if args.list_dd_builds:
        return _print_saved_dd_builds(Path(args.builds))

    if not str(args.build or "").strip():
        parser.error("--build is required unless --list-dd-builds is used")
    if args.target_health is None:
        parser.error("--target-health is required unless --list-dd-builds is used")
    if args.target_resistance is None:
        parser.error("--target-resistance is required unless --list-dd-builds is used")

    if args.duration <= 0:
        raise ValueError("duration must be positive")
    if args.target_health <= 0:
        raise ValueError("target health must be positive")
    if args.target_resistance < 0:
        raise ValueError("target resistance cannot be negative")

    try:
        build = _load_build(Path(args.builds), args.build, args.character)
    except ValueError as exc:
        print(str(exc))
        print()
        print("Available saved DD/DPS builds:")
        builds = _saved_dd_builds(Path(args.builds))
        if builds:
            for candidate in builds:
                print(
                    f"  {_character_name(candidate) or '(unnamed character)'} | "
                    f"{getattr(candidate, 'BuildName', '') or '(unnamed build)'}"
                )
        else:
            print("  none")
        return 2
    role = " ".join(
        str(getattr(build, "Role", "") or "")
        .strip()
        .casefold()
        .replace("_", " ")
        .split()
    )
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "saved-build Combat Simulation audit requires a DD/DPS build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=float(args.duration),
            weave_light_attacks=not bool(args.no_weave),
            ultimate_bar=str(args.ultimate_bar or ""),
            starting_ultimate=float(args.starting_ultimate),
            use_scheduled_combat_attacks_for_ultimate=bool(
                args.use_scheduled_attacks_for_ultimate
            ),
        ),
    )
    plan = generated.plan

    database_path = Path(args.database)
    builds_path = Path(args.builds)
    raw_static = RotationStaticBuildContextService(
        database_path=database_path,
        builds_path=builds_path,
    )
    dd_static = RotationDDRelevantStaticContextService(raw_static)
    static_resolution = dd_static.resolve(build)
    if not static_resolution.resolved:
        print("=" * 76)
        print(" PHASE 14 SAVED-BUILD COMBAT SIMULATION")
        print("=" * 76)
        print(f"Character: {_character_name(build) or 'unnamed'}")
        print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
        print()
        print("STATIC DD PREREQUISITES")
        print("-----------------------")
        for message in static_resolution.unresolved:
            print(message)
        return 2

    progression = static_resolution.progression.progression
    if progression is None:
        raise RuntimeError("resolved DD static context did not expose progression")

    attacker_state_service = CombatSimulationPlanAttackerStateService(
        potion_state_service=RotationPlanPotionCombatStateService(database_path),
    )
    attacker_state_resolver = attacker_state_service.resolver(
        build,
        progression=progression,
        plan=plan,
    )
    runtime_context_service = RotationPlanRuntimeBuildContextService(
        static_context_service=dd_static,
    )

    def runtime_build_context_resolver(
        time_seconds: float,
        sequence: int | None = None,
    ):
        return runtime_context_service.resolve(
            build,
            runtime_combat_state_resolver=attacker_state_resolver,
            time_seconds=time_seconds,
            sequence=sequence,
        )

    windows = tuple(_parse_window(raw) for raw in tuple(args.off_balance_window or ()))
    target_state_known = bool(args.target_state_known or windows)
    target_combat_state_resolver = (
        RotationExplicitTargetCombatStateScheduleService(windows)
        if target_state_known
        else None
    )

    def target_resistance_resolver(
        _time_seconds: float,
        _sequence: int | None = None,
    ) -> float:
        return float(args.target_resistance)

    anchor_evidence = tuple(
        parse_explicit_impact_anchor(raw)
        for raw in tuple(args.impact_anchor or ())
    )
    activation_anchor_resolver = build_explicit_activation_anchor_resolver(
        plan=plan,
        evidence=anchor_evidence,
    )

    target_name = str(args.target_name or "Boss").strip() or "Boss"
    target_state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                target_name,
                "enemy",
                current_health=int(args.target_health),
                maximum_health=int(args.target_health),
            ),
        ),
    )

    provider_service = CombatSimulationSavedBuildDDProviderService(
        database_path=database_path,
        static_context_service=raw_static,
    )
    simulator = CombatSimulationSavedBuildDDService(
        provider_service=provider_service,
    )
    build_snapshot = EffectiveBuildSnapshot.from_saved_build(build)

    def run_once():
        return simulator.simulate(
            build_snapshot=build_snapshot,
            plan=plan,
            target_state=target_state,
            damage_target_identity=target_name,
            target_resistance=float(args.target_resistance),
            target_combat_state_resolver=target_combat_state_resolver,
            target_resistance_resolver=target_resistance_resolver,
            runtime_build_context_resolver=runtime_build_context_resolver,
            activation_anchor_resolver=activation_anchor_resolver,
        )

    replay = CombatSimulationDeterministicReplayService().verify(run_once)
    result = replay.first
    if not replay.deterministic:
        result = replace(
            result,
            unresolved=tuple(
                dict.fromkeys(
                    (
                        *result.unresolved,
                        "deterministic replay mismatch: "
                        + ", ".join(replay.differing_signature_fields),
                    )
                )
            ),
        )
    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity=target_name,
    )

    print("=" * 76)
    print(" PHASE 14 SAVED-BUILD COMBAT SIMULATION")
    print("=" * 76)
    print(f"Character:             {_character_name(build) or 'unnamed'}")
    print(f"Build:                 {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Role:                  {getattr(build, 'Role', '') or 'unresolved'}")
    print(f"Planned duration:      {float(plan.duration_seconds):g}s")
    print(f"Executed duration:     {summary.duration_seconds:g}s")
    print(f"Generated actions:     {len(plan.actions)}")
    print(
        "Deterministic replay:  "
        + (
            "PASS"
            if replay.deterministic
            else "FAIL (" + ", ".join(replay.differing_signature_fields) + ")"
        )
    )
    print(f"Target:                {target_name}")
    print(f"Starting Health:       {int(args.target_health):,}")
    print(f"Target resistance:     {float(args.target_resistance):g}")
    print(
        "Target CombatState:    "
        + ("authoritative explicit schedule" if target_state_known else "unresolved when required")
    )
    print(
        "Activation anchors:    "
        + (
            f"{len(anchor_evidence)} explicit non-cast anchor(s)"
            if anchor_evidence
            else "cast anchors only; reviewed non-cast anchors remain unresolved"
        )
    )
    print()

    print("RESULT")
    print("------")
    print(f"Outgoing events:       {summary.outgoing_event_count}")
    print(f"Attempted damage:      {summary.attempted_damage:,.2f}")
    print(f"Applied damage:        {summary.applied_damage:,.2f}")
    print(f"Overkill:              {summary.total_overkill:,.2f}")
    print(
        f"Ending Health:         "
        + (
            f"{summary.ending_target_health:,}"
            if summary.ending_target_health is not None
            else "unknown"
        )
    )
    print(
        f"Ending Health percent: "
        f"{_format_pct(summary.ending_target_health, summary.target_maximum_health)}"
    )
    print(f"Target dead:           {'yes' if summary.target_dead else 'no'}")
    if summary.death_time_seconds is not None:
        print(f"Death time:            {summary.death_time_seconds:g}s")
    if summary.killing_source is not None:
        print(f"Killing source:        {summary.killing_source}")
    if summary.modeled_dps is None:
        print("Modeled DPS:           withheld (unresolved damage evidence remains)")
    else:
        print(f"Modeled DPS:           {summary.modeled_dps:,.2f}")
    print()

    print("DAMAGE BY SOURCE")
    print("----------------")
    if summary.damage_by_source:
        for row in summary.damage_by_source:
            kill = " | KILL" if row.killing_blow else ""
            print(
                f"{row.attempted_damage:12,.2f} attempted | "
                f"{row.applied_damage:12,.2f} applied | "
                f"{row.overkill:10,.2f} overkill | "
                f"{row.event_count:4d} raw event(s) | {row.source}{kill}"
            )
    else:
        print("none")
    print()

    print("UNRESOLVED")
    print("----------")
    if summary.unresolved:
        for index, message in enumerate(summary.unresolved, start=1):
            print(f"{index:3d}. {message}")
    else:
        print("none")
    print()

    if args.show_events:
        print("DAMAGE / HEALTH EVENT TIMELINE")
        print("------------------------------")
        for event in result.events:
            if event.event_type not in {"outgoing_damage", "health_change", "death"}:
                continue
            payload = event.payload_dict()
            if event.event_type == "outgoing_damage":
                print(
                    f"{event.time_seconds:8.3f}s #{event.sequence:<3d} "
                    f"DAMAGE {float(payload.get('amount') or 0.0):12,.2f} | {event.source}"
                )
            elif event.event_type == "health_change":
                print(
                    f"{event.time_seconds:8.3f}s #{event.sequence:<3d} "
                    f"HEALTH {payload.get('before')} -> {payload.get('after')} | {event.source}"
                )
            else:
                print(
                    f"{event.time_seconds:8.3f}s #{event.sequence:<3d} DEATH | {event.source}"
                )
        print()

    print(
        "Interpretation: this is the deterministic modeled damage currently proven by "
        "the saved build, generated plan, reviewed runtime semantics, and caller-owned "
        "target assumptions. A DPS number is withheld whenever any damage consequence "
        "remains unresolved."
    )
    return 0 if not summary.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
