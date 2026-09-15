from __future__ import annotations

"""Read-only end-to-end acceptance audit for one persisted Raid Plan.

The audit intentionally separates application-pipeline health from plan readiness.
It reads the user's actual saved Raid Plan/build data, but round-trips persistence only
through a temporary repository. It never mutates raid_plans.json, builds.json, Personnel,
or Rotation state.

Flow exercised:

    persisted RaidPlan
      -> exact saved-build resolution
      -> canonical Coverage evidence
      -> RaidPlan EffectiveBuildSnapshot boundary used by Rotation
      -> read-only Optimizer Adviser review

Usage examples:

    python tools/audit_raid_plan_acceptance.py
    python tools/audit_raid_plan_acceptance.py --plan "Performance Mode"
    python tools/audit_raid_plan_acceptance.py --plan-id rockgrove-plan
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from engine.config import DEFAULT_DATABASE, get_data_dir
from models.effective_build_snapshot import EffectiveBuildSnapshot
from models.raid_plan import RaidPlan
from services.build_service import BuildService
from services.raid_group_effect_catalog import GROUP_COVERAGE_NAMES
from services.raid_named_group_effect_capability_service import (
    RaidNamedGroupEffectCapabilityService,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_plan_optimizer_adviser_service import RaidPlanOptimizerAdviserService
from services.raid_plan_repository import RaidPlanRepository
from services.raid_unique_support_set_capability_service import (
    RaidUniqueSupportSetCapabilityService,
)
from services.raid_unique_support_set_catalog import UNIQUE_SUPPORT_SET_NAMES
from services.saved_build_capability_service import (
    RaidCoverageSnapshot,
    SavedBuildCapabilityService,
    summarize_raid_coverage,
)
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE


FULL_COVERAGE_NAMES = tuple(
    dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES))
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _extend_snapshot(snapshot: RaidCoverageSnapshot) -> RaidCoverageSnapshot:
    status = {name: "unverified" for name in FULL_COVERAGE_NAMES}
    providers = {name: [] for name in FULL_COVERAGE_NAMES}
    conditional = {name: [] for name in FULL_COVERAGE_NAMES}
    for name in FULL_COVERAGE_NAMES:
        if name in snapshot.status:
            status[name] = snapshot.status[name]
        if name in snapshot.providers:
            providers[name] = list(snapshot.providers[name])
        if name in snapshot.conditional_providers:
            conditional[name] = list(snapshot.conditional_providers[name])
    return RaidCoverageSnapshot(status, providers, conditional)


@dataclass(frozen=True)
class RaidPlanAcceptanceResult:
    plan: RaidPlan
    saved_build_count: int
    resolved_build_count: int
    unresolved: tuple[str, ...]
    persistence_roundtrip_ok: bool
    effective_snapshot_count: int
    identified_effects: tuple[tuple[str, str, tuple[str, ...]], ...]
    adviser_blockers: int
    adviser_actionable: int
    adviser_findings: tuple[tuple[str, str, str], ...]

    @property
    def pipeline_ok(self) -> bool:
        return self.persistence_roundtrip_ok and self.effective_snapshot_count == self.resolved_build_count

    @property
    def plan_has_resolved_builds(self) -> bool:
        return self.resolved_build_count > 0


def _choose_plan(
    plans: tuple[RaidPlan, ...],
    *,
    plan_id: str = "",
    plan_name: str = "",
) -> RaidPlan:
    if not plans:
        raise ValueError("no saved Raid Plans were found")

    wanted_id = _clean(plan_id).casefold()
    if wanted_id:
        matches = tuple(plan for plan in plans if plan.plan_id.casefold() == wanted_id)
        if len(matches) != 1:
            raise ValueError(f"plan id {plan_id!r} did not resolve to exactly one saved Raid Plan")
        return matches[0]

    wanted_name = _clean(plan_name).casefold()
    if wanted_name:
        exact = tuple(plan for plan in plans if plan.name.casefold() == wanted_name)
        if len(exact) == 1:
            return exact[0]
        contains = tuple(plan for plan in plans if wanted_name in plan.name.casefold())
        if len(contains) == 1:
            return contains[0]
        raise ValueError(
            f"plan name {plan_name!r} did not resolve to exactly one saved Raid Plan"
        )

    if len(plans) == 1:
        return plans[0]
    names = ", ".join(f"{plan.plan_id} ({plan.name})" for plan in plans)
    raise ValueError(
        "multiple saved Raid Plans exist; choose one with --plan-id or --plan. "
        f"Available: {names}"
    )


def audit_raid_plan(
    *,
    plan: RaidPlan,
    saved_builds,
    capability_service,
) -> RaidPlanAcceptanceResult:
    saved = tuple(saved_builds)

    with TemporaryDirectory(prefix="bff-raid-plan-acceptance-") as temp_dir:
        repository = RaidPlanRepository(Path(temp_dir) / "raid_plans.json")
        repository.save(plan)
        round_tripped = repository.get(plan.plan_id)
        persistence_ok = round_tripped == plan

    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=saved,
        coverage_effect_names=FULL_COVERAGE_NAMES,
    )

    audits = tuple(
        (member.build, capability_service.audit_build(member.build))
        for member in scope.members
    )
    snapshot = _extend_snapshot(
        summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, audits)
    )
    snapshot = RaidNamedGroupEffectCapabilityService().overlay(
        snapshot,
        scope.resolved_builds,
        capability_service=capability_service,
    )
    snapshot = RaidUniqueSupportSetCapabilityService().overlay(
        snapshot,
        scope.resolved_builds,
    )

    identified: list[tuple[str, str, tuple[str, ...]]] = []
    for effect_name in FULL_COVERAGE_NAMES:
        state = snapshot.status.get(effect_name, "unverified")
        providers = tuple(snapshot.providers.get(effect_name, ()))
        conditional = tuple(snapshot.conditional_providers.get(effect_name, ()))
        if state in {"available", "conditional"}:
            identified.append((effect_name, state, providers or conditional))

    effective_snapshots = []
    for member in scope.members:
        raid_member = plan.member(member.seat_id)
        if raid_member is None:
            raise ValueError(f"resolved Coverage chair disappeared from RaidPlan: {member.seat_id}")
        snapshot_build = EffectiveBuildSnapshot.from_raid_plan_build(
            member.build,
            character_id=raid_member.character_id,
            trial_id=plan.trial_id,
            team_name=plan.team_name,
            provenance=(
                f"raid_plan:{plan.plan_id}",
                f"seat:{member.seat_id}",
                f"build:{raid_member.selected_build_name or member.build.BuildName}",
            ),
        )
        if not snapshot_build.matches(member.build):
            raise ValueError(f"effective build fingerprint mismatch for {member.seat_id}")
        effective_snapshots.append(snapshot_build)

    adviser = RaidPlanOptimizerAdviserService(capability_service).review(
        raid_plan=plan,
        saved_builds=saved,
    )
    adviser_findings = tuple(
        (finding.category, finding.subject, finding.recommendation)
        for finding in adviser.findings
    )

    return RaidPlanAcceptanceResult(
        plan=plan,
        saved_build_count=len(saved),
        resolved_build_count=len(scope.members),
        unresolved=scope.unresolved,
        persistence_roundtrip_ok=persistence_ok,
        effective_snapshot_count=len(effective_snapshots),
        identified_effects=tuple(identified),
        adviser_blockers=adviser.blocker_count,
        adviser_actionable=adviser.actionable_count,
        adviser_findings=adviser_findings,
    )


def _print_result(result: RaidPlanAcceptanceResult) -> None:
    plan = result.plan
    print("=" * 76)
    print(" RAID PLAN END-TO-END ACCEPTANCE AUDIT")
    print("=" * 76)
    print(f"Plan: {plan.name} ({plan.plan_id})")
    print(f"Trial: {plan.trial_id} | Difficulty: {plan.difficulty or 'unspecified'}")
    print(f"Named chairs: {len(plan.members)}/12")
    print(f"Saved builds available: {result.saved_build_count}")
    print(f"Exact selected builds resolved: {result.resolved_build_count}")
    print(f"Persistence temp round-trip: {'PASS' if result.persistence_roundtrip_ok else 'FAIL'}")
    print(
        "Rotation effective-build snapshots: "
        f"{result.effective_snapshot_count}/{result.resolved_build_count}"
    )

    if result.unresolved:
        print("\nUNRESOLVED CHAIRS / BUILDS")
        for item in result.unresolved:
            print(f"- {item}")

    print("\nIDENTIFIED RAID-FACING EFFECTS")
    if result.identified_effects:
        for effect, state, providers in result.identified_effects:
            print(f"- {effect}: {state} via {', '.join(providers)}")
    else:
        print("- None identified from the exact resolved builds.")

    print("\nOPTIMIZER ADVISER")
    print(f"Blockers: {result.adviser_blockers} | Actionable review items: {result.adviser_actionable}")
    if result.adviser_findings:
        for category, subject, recommendation in result.adviser_findings[:12]:
            print(f"- [{category.upper()}] {subject}: {recommendation}")
        if len(result.adviser_findings) > 12:
            print(f"- +{len(result.adviser_findings) - 12} more finding(s)")
    else:
        print("- No Adviser findings.")

    print("\nPIPELINE RESULT")
    if not result.pipeline_ok:
        print("FAIL - one or more application handoff invariants failed.")
    elif not result.plan_has_resolved_builds:
        print("PARTIAL - pipeline is healthy, but this plan has no exact selected builds to evaluate.")
    else:
        print("PASS - Save/Load, Coverage, Rotation build boundary, and Adviser all consumed the same Raid Plan/build truth.")
    if result.adviser_blockers or result.unresolved:
        print("PLAN READINESS: REVIEW REQUIRED - plan blockers are not pipeline failures.")
    else:
        print("PLAN READINESS: no structural blocker surfaced by this acceptance audit.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-id", default="", help="Exact persisted RaidPlan.plan_id")
    parser.add_argument("--plan", default="", help="Exact or unique partial saved Raid Plan name")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=get_data_dir(),
        help="Foundry data directory containing raid_plans.json and builds.json",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Canonical ESO database used by saved-build capability analysis",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    plan_repository = RaidPlanRepository(data_dir / "raid_plans.json")
    plans = plan_repository.list_plans()
    try:
        plan = _choose_plan(plans, plan_id=args.plan_id, plan_name=args.plan)
    except ValueError as exc:
        print(f"Raid Plan acceptance audit could not select a plan: {exc}")
        return 2

    build_service = BuildService(data_dir / "builds.json")
    roster = build_service.load()
    saved_builds = tuple(getattr(roster, "Members", ()) or ())
    capability_service = SavedBuildCapabilityService(build_service, Path(args.database))

    result = audit_raid_plan(
        plan=plan,
        saved_builds=saved_builds,
        capability_service=capability_service,
    )
    _print_result(result)
    return 0 if result.pipeline_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
