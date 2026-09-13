from __future__ import annotations

"""Apply only jointly selected cross-bar routes to one explicit-priority DD plan."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationActionKind
from services.rotation_cross_bar_filler_opportunity_service import (
    RotationCrossBarFillerOpportunityService,
)
from services.rotation_cross_bar_route_mutation_service import (
    RotationCrossBarRouteMutationService,
)
from services.rotation_cross_bar_route_proposal_service import (
    RotationCrossBarRouteProposalService,
)
from services.rotation_cross_bar_route_selection_service import (
    RotationCrossBarRouteSelectionService,
)
from services.rotation_cross_bar_route_slot_feasibility_service import (
    RotationCrossBarRouteSlotFeasibilityService,
)
from tools.audit_phase13_dd_priority_schedule import _character_name, _priority_entries
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="BAR:SLOT:PRIORITY",
        help="Rank every occupied ordinary saved slot; lower numbers are higher priority.",
    )
    parser.add_argument(
        "--no-weave",
        action="store_true",
        help="Disable normal light-attack weaving for this diagnostic mutation.",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("duration must be positive")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD route mutation audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    priorities = _priority_entries(tuple(args.priority or ()), build=build)
    priority_list = AbilityPriorityList(
        character_name=_character_name(build),
        build_name=str(getattr(build, "BuildName", "") or "").strip(),
        role=str(getattr(build, "Role", "") or "Unspecified").strip(),
        entries=priorities,
    )
    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=not bool(args.no_weave),
            ability_priorities=priorities,
        ),
    )

    opportunities = RotationCrossBarFillerOpportunityService().find(
        generated.plan,
        priorities=priority_list,
    )
    proposals = RotationCrossBarRouteProposalService().propose(
        generated.plan,
        opportunities,
    )
    feasibility = RotationCrossBarRouteSlotFeasibilityService().assess(
        generated.plan,
        proposals,
    )
    selection = RotationCrossBarRouteSelectionService().select(
        generated.plan,
        proposals,
        feasibility,
    )
    mutation = RotationCrossBarRouteMutationService().apply(
        generated.plan,
        selection,
        weave_light_attacks=not bool(args.no_weave),
    )

    assessor = RotationActiveBarAssessor()
    before_legality = assessor.assess(generated.plan)
    after_legality = assessor.assess(mutation.plan)

    before_waits = sum(
        1 for action in generated.plan.actions if action.kind is RotationActionKind.WAIT
    )
    after_waits = sum(
        1 for action in mutation.plan.actions if action.kind is RotationActionKind.WAIT
    )
    before_skills = sum(
        1 for action in generated.plan.actions if action.kind is RotationActionKind.SKILL
    )
    after_skills = sum(
        1 for action in mutation.plan.actions if action.kind is RotationActionKind.SKILL
    )
    before_swaps = sum(
        1 for action in generated.plan.actions if action.kind is RotationActionKind.BAR_SWAP
    )
    after_swaps = sum(
        1 for action in mutation.plan.actions if action.kind is RotationActionKind.BAR_SWAP
    )

    print("=" * 72)
    print(" PHASE 13 DD SELECTED CROSS-BAR ROUTE MUTATION AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print(f"Weaving:   {'off' if args.no_weave else 'on'}")
    print()

    print("ROUTE SELECTION")
    print("---------------")
    print(f"opportunities={len(opportunities)}")
    print(f"proposals={len(proposals)}")
    print(f"slot_feasible={sum(1 for row in feasibility if row.feasible)}")
    print(f"selected={len(selection.selected)}")
    print(f"rejected={len(selection.rejected)}")
    for row in selection.selected:
        proposal = row.proposal
        reserved = ",".join(f"{value:g}" for value in row.reserved_wait_times)
        print(
            f"  SELECTED {proposal.wait_time_seconds:g}s | "
            f"{proposal.source_bar}->{proposal.target_bar} | "
            f"{proposal.filler_skill_name} | reserved={reserved}"
        )
    print()

    print("MUTATION DELTA")
    print("--------------")
    print(f"wait_actions:  {before_waits} -> {after_waits}")
    print(f"skill_actions: {before_skills} -> {after_skills}")
    print(f"bar_swaps:     {before_swaps} -> {after_swaps}")
    print(
        "consumed_wait_times="
        + (
            ",".join(f"{value:g}" for value in mutation.consumed_wait_times)
            if mutation.consumed_wait_times
            else "none"
        )
    )
    print(f"unresolved:    {len(generated.plan.unresolved)} -> {len(mutation.plan.unresolved)}")
    print()

    print("ACTIVE-BAR LEGALITY")
    print("-------------------")
    print(f"before_legal={before_legality.legal} violations={len(before_legality.violations)}")
    print(f"after_legal={after_legality.legal} violations={len(after_legality.violations)}")
    if after_legality.violations:
        for violation in after_legality.violations:
            print(
                f"  {violation.time_seconds:g}s | {violation.action_kind.value} "
                f"{violation.action_name} | scheduled={violation.scheduled_bar} "
                f"active={violation.active_bar} | {violation.reason}"
            )
    print()

    print("MUTATED ACTIONS AT CONSUMED WAIT TIMES")
    print("--------------------------------------")
    consumed = set(mutation.consumed_wait_times)
    for action in mutation.plan.actions:
        if not any(abs(float(action.time_seconds) - value) <= 1e-9 for value in consumed):
            continue
        print(
            f"{action.time_seconds:g}s #{action.sequence} | {action.kind.value} | "
            f"{action.name or '<none>'} | bar={action.bar or '<none>'}"
        )
    print()

    print("REMAINING PLAN-LEVEL UNRESOLVED")
    print("-------------------------------")
    if mutation.plan.unresolved:
        for item in mutation.plan.unresolved:
            print(item)
    else:
        print("none")
    print()
    print(
        "Interpretation: this audit mutates only jointly selected routes proven legal "
        "under the current one-second BAR_SWAP model. Rejected routes remain untouched; "
        "the production Generate path is not changed by this diagnostic."
    )
    return 0 if after_legality.legal else 2


if __name__ == "__main__":
    raise SystemExit(main())
