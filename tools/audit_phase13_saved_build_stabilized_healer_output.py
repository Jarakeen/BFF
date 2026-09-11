from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
    RotationCandidateHealerRoleOutputService,
)
from services.rotation_healer_output_context_relevance_service import (
    RotationHealerOutputContextRelevanceService,
)
from services.rotation_healer_reviewed_runtime_evidence_loader import (
    RotationHealerReviewedRuntimeEvidenceLoader,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
)
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateService,
)
from services.rotation_recovery_healer_role_output_service import (
    RotationRecoveryHealerRoleOutputService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from tools.audit_phase13_saved_build_recovery_heavy_rotation import (
    DEFAULT_BUILDS,
    _baseline_maximum_magicka,
    _character_name,
    _load_saved_build,
    build_verified_heavy_restore_resolver,
)
from tools.rotation_runtime_snapshot_fixture import (
    load_rotation_runtime_snapshot_fixture,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


def _full_fight_demand(duration_seconds: float) -> RotationDemandWindow:
    duration = float(duration_seconds)
    if duration <= 0:
        raise ValueError("healer output audit duration must be positive")
    return RotationDemandWindow(
        name="full stabilized healer-output audit",
        start_seconds=0.0,
        end_seconds=duration,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
        target_count=12,
    )


def _load_reviewed_periodic_observations(
    database_path: Path,
    fixture_path: Path | None,
    refresh_fixture_path: Path | None,
):
    report = RotationHealerReviewedRuntimeEvidenceLoader(database_path).load(
        fixture_path,
        refresh_fixture_path=refresh_fixture_path,
    )
    return tuple(report.observations), tuple(report.unresolved)


def _runtime_mode_label(runtime_snapshot_path: Path | None) -> str:
    if runtime_snapshot_path is None:
        return "STATIC FALLBACK; snapshot has no authoritative runtime history"
    return "EXACT-TIME RUNTIME HISTORY; explicit fixture bound to final stabilized plan"


def _print_healing_evidence(evidence) -> None:
    print("HEALING CONSEQUENCES")
    print("--------------------")
    print(
        f"Direct events:       {len(evidence.direct_events):4d} | "
        f"modeled={evidence.modeled_direct_healing:g}"
    )
    print(
        f"Periodic events:     {len(evidence.periodic_events):4d} | "
        f"modeled={evidence.modeled_periodic_healing:g}"
    )
    print(
        f"Delayed events:      {len(evidence.delayed_events):4d} | "
        f"modeled={evidence.modeled_delayed_healing:g}"
    )
    print(
        f"Channel events:      {len(evidence.channel_events):4d} | "
        f"modeled={evidence.modeled_channel_healing:g}"
    )
    print(
        "External conditional:      "
        f"modeled={evidence.modeled_external_conditional_healing:g}"
    )
    print(f"Modeled total:             {evidence.modeled_total_healing:g}")
    print()
    print("UNRESOLVED HEALING CONSEQUENCES")
    print("-------------------------------")
    if evidence.unresolved:
        for item in evidence.unresolved:
            print(f"- {item}")
    else:
        print("none")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a real saved healer build through recovery-heavy stabilization, then audit "
            "canonical healing consequences on the exact final stabilized plan."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--maximum-magicka",
        type=int,
        help="optional override; otherwise derived from the Phase 4 full-pool sustain baseline",
    )
    parser.add_argument("--trigger-fraction", type=float, required=True)
    parser.add_argument(
        "--restore-amount",
        type=int,
        required=True,
        help="caller-verified fully charged heavy Magicka restore amount",
    )
    parser.add_argument("--restore-bar", choices=("front", "back"))
    parser.add_argument("--channel-seconds", type=float, default=1.8)
    parser.add_argument("--max-iterations", type=int, default=6)
    parser.add_argument(
        "--runtime-observations",
        type=Path,
        default=None,
        help="optional reviewed healer periodic-runtime timing observation fixture",
    )
    parser.add_argument(
        "--refresh-policies",
        type=Path,
        default=None,
        help="optional reviewed healer periodic refresh/recast policy fixture",
    )
    parser.add_argument(
        "--runtime-snapshot",
        type=Path,
        default=None,
        help=(
            "optional explicit authoritative runtime-history fixture; omitted preserves "
            "the static fallback path without inventing runtime events"
        ),
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("--duration must be positive")
    if not 0 < float(args.trigger_fraction) <= 1:
        raise ValueError("--trigger-fraction must be in (0, 1]")
    if int(args.restore_amount) <= 0:
        raise ValueError("--restore-amount must be positive")
    if float(args.channel_seconds) <= 0:
        raise ValueError("--channel-seconds must be positive")
    if int(args.max_iterations) <= 0:
        raise ValueError("--max-iterations must be positive")

    builds_path = Path(args.builds)
    database_path = Path(args.database)
    runtime_snapshot_path = (
        None if args.runtime_snapshot is None else Path(args.runtime_snapshot)
    )
    build = _load_saved_build(
        builds_path,
        character=args.character,
        build_name=args.build,
    )
    maximum_magicka = (
        int(args.maximum_magicka)
        if args.maximum_magicka is not None
        else _baseline_maximum_magicka(
            build=build,
            duration_seconds=duration,
            database_path=database_path,
        )
    )
    if maximum_magicka <= 0:
        raise ValueError("maximum Magicka must be positive")

    restore_resolver = build_verified_heavy_restore_resolver(
        amount=int(args.restore_amount),
        channel_seconds=float(args.channel_seconds),
        bar=args.restore_bar,
    )
    generation = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            required_heavy_channel_seconds=float(args.channel_seconds),
            stabilize_recovery_heavies=True,
            recovery_stabilization_resource=ResourceType.MAGICKA,
            recovery_maximum_amount=maximum_magicka,
            recovery_trigger_fraction=float(args.trigger_fraction),
            recovery_restoration_resolver=restore_resolver,
            recovery_stabilization_max_iterations=int(args.max_iterations),
        ),
    )
    stabilization = generation.recovery_stabilization
    if stabilization is None:
        raise RuntimeError("recovery-heavy stabilization evidence was not returned")

    static_service = RotationStaticBuildContextService(
        builds_path=builds_path,
        database_path=database_path,
    )
    static_contexts = static_service.resolve(build)
    front_context = static_contexts.context_for("front")
    back_context = static_contexts.context_for("back")
    if front_context is None or back_context is None:
        detail = "; ".join(static_contexts.unresolved) or "no usable static contexts"
        raise RuntimeError(
            "stabilized healer-output audit requires front and back contexts: " + detail
        )

    context_relevance = RotationHealerOutputContextRelevanceService().classify(
        static_contexts.unresolved
    )
    periodic_observations, fixture_unresolved = _load_reviewed_periodic_observations(
        database_path,
        args.runtime_observations,
        args.refresh_policies,
    )

    demand = _full_fight_demand(duration)
    demand_provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path=database_path,
        build=build,
        context=front_context,
        contexts_by_bar={"front": front_context, "back": back_context},
        reviewed_runtime_observations=periodic_observations,
    )
    role_output = RotationCandidateHealerRoleOutputService(
        demand=demand,
        demand_evidence_provider=demand_provider,
    )
    runtime_build_context = RotationPlanRuntimeBuildContextService(
        static_context_service=static_service,
    )
    stabilized_role_output = RotationRecoveryHealerRoleOutputService(
        build=build,
        role_output_service=role_output,
        runtime_build_context_service=runtime_build_context,
    )

    runtime_combat_state_resolver = None
    runtime_build_context_resolver = None
    if runtime_snapshot_path is not None:
        runtime_snapshot = load_rotation_runtime_snapshot_fixture(runtime_snapshot_path)
        progression = static_service.progression_adapter.resolve(build)
        if not progression.resolved:
            detail = "; ".join(progression.unresolved) or "progression is unresolved"
            raise RuntimeError(
                "runtime-bound stabilized healer-output audit requires canonical progression: "
                + detail
            )
        plan_runtime_state = RotationPlanRuntimeCombatStateService(
            runtime_snapshot_state=ExtremeRuntimeSnapshotCombatStateService(database_path)
        )

        def runtime_combat_state_resolver(
            time_seconds: float,
            sequence: int | None = None,
        ):
            return plan_runtime_state.resolve(
                build,
                progression=progression.progression,
                plan=stabilization.plan,
                runtime_snapshot_source=runtime_snapshot,
                time_seconds=time_seconds,
                sequence=sequence,
                initial_bar="front",
                base_combat_state=front_context.combat_state,
            )

        def runtime_build_context_resolver(
            time_seconds: float,
            sequence: int | None = None,
        ):
            return runtime_build_context.resolve(
                build,
                runtime_combat_state_resolver=runtime_combat_state_resolver,
                time_seconds=time_seconds,
                sequence=sequence,
            )

    snapshot = RecoveryHeavyStabilizedCandidateSnapshot(
        candidate_id="saved-build-stabilized",
        plan=stabilization.plan,
        replay=stabilization.replay,
        stabilization=stabilization,
        runtime_combat_state_resolver=runtime_combat_state_resolver,
    )
    final_role_output = stabilized_role_output.evaluate_snapshot(snapshot)

    detailed_candidate = GeneratedRotationCandidate(
        candidate_id=snapshot.candidate_id,
        plan=snapshot.plan,
        refresh_leads=(),
        action_claims=(),
    )
    detailed_kwargs = {
        "candidate": detailed_candidate,
        "demand": demand,
    }
    if runtime_build_context_resolver is not None:
        detailed_kwargs["runtime_build_context_resolver"] = runtime_build_context_resolver
    detailed_evidence = demand_provider.evaluate_demand(**detailed_kwargs)

    print("=" * 100)
    print(" PHASE 13 SAVED-BUILD STABILIZED HEALER OUTPUT AUDIT")
    print("=" * 100)
    print(f"Character:           {_character_name(build) or 'unnamed'}")
    print(f"Build:               {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Role:                {getattr(build, 'Role', '') or 'Unspecified'}")
    print(f"Duration:            {duration:g}s")
    print(f"Maximum Magicka:     {maximum_magicka}")
    print(f"Recovery trigger:    {float(args.trigger_fraction):.1%}")
    print(f"Heavy restore:       {int(args.restore_amount)} Magicka (caller verified)")
    print(f"Heavy channel:       {float(args.channel_seconds):g}s")
    print(f"Restore bar:         {args.restore_bar or 'any scheduled heavy'}")
    print(f"Stabilization:       {'CONVERGED' if stabilization.converged else 'NOT CONVERGED'}")
    print(f"Iterations:          {len(stabilization.iterations)}")
    print(f"Runtime evaluation:  {_runtime_mode_label(runtime_snapshot_path)}")
    print(
        "Output unit:         modeled pre-recipient, pre-overheal healing per second over "
        "the full audit window"
    )
    print()

    if context_relevance.ambient:
        print("Ambient static-context diagnostics:")
        for item in context_relevance.ambient:
            print(f"  - {item}")
        print()
    if context_relevance.relevant:
        print("Healing-relevant static-context blockers:")
        for item in context_relevance.relevant:
            print(f"  - {item}")
        print()
    if fixture_unresolved:
        print("Reviewed runtime fixture diagnostics:")
        for item in fixture_unresolved:
            print(f"  - {item}")
        print()

    _print_healing_evidence(detailed_evidence)
    print()
    print("FINAL STABILIZED ROLE OUTPUT")
    print("----------------------------")
    if final_role_output.value is None:
        print("Modeled healer output: UNRESOLVED")
    else:
        print(f"Modeled healer output: {final_role_output.value:g} healing/second")
    if final_role_output.unresolved:
        print("Role-output blockers:")
        for item in final_role_output.unresolved:
            print(f"  - {item}")
    else:
        print("Role-output blockers: none")

    print()
    print("BOUNDARIES")
    print("----------")
    print("- The audited plan is the exact final recovery-stabilized plan, not the seed schedule.")
    print("- Heavy restore amount remains caller-verified because live base restoration is not canonicalized.")
    if runtime_snapshot_path is None:
        print("- No runtime CombatState history is fabricated; this invocation intentionally exercises static fallback.")
    else:
        print("- Runtime CombatState comes only from the explicit authoritative runtime-history fixture supplied by the caller.")
    print("- Missing periodic, delayed, channel, or conditional healing evidence remains explicit and fail-closed.")
    print("- Modeled healing is not recipient assignment, overheal, observed HPS, or an encounter survival threshold.")

    unresolved = tuple(
        dict.fromkeys(
            tuple(context_relevance.relevant)
            + tuple(fixture_unresolved)
            + tuple(detailed_evidence.unresolved)
            + tuple(final_role_output.unresolved)
        )
    )
    if not stabilization.converged:
        return 2
    return 3 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
