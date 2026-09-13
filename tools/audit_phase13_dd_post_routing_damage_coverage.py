from __future__ import annotations

"""Audit canonical DD damage coverage on the final priority-routed production plan."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_dd_whole_plan_damage_blocker_triage_service import (
    RotationDDWholePlanDamageBlockerTriageService,
)
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDWholePlanDamageCoverageAuditService,
)
from services.rotation_explicit_target_combat_state_schedule_service import (
    RotationExplicitTargetCombatStateScheduleService,
)
from tools.audit_phase13_dd_priority_schedule import _character_name, _priority_entries
from tools.audit_phase13_dd_whole_plan_damage_coverage import (
    _action_damage_provider,
    _parse_target_window,
    _print_triage_section,
)
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from tools.dd_audit_activation_anchor_support import (
    build_explicit_activation_anchor_resolver,
    parse_explicit_impact_anchor,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_generation_support import RotationGenerationRequest


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "eso.db")
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--target-resistance", type=float, required=True)
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="BAR:SLOT:PRIORITY",
        help="Rank every occupied ordinary saved-bar slot; lower number is higher priority.",
    )
    parser.add_argument(
        "--target-state-known",
        action="store_true",
        help="Treat target CombatState as authoritative outside named windows.",
    )
    parser.add_argument(
        "--off-balance-window",
        action="append",
        default=[],
        metavar="START:END",
    )
    parser.add_argument(
        "--impact-anchor",
        action="append",
        default=[],
        metavar="SKILL:ACTION_TIME:SEQUENCE:IMPACT_TIME",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("duration must be positive")
    target_resistance = float(args.target_resistance)
    if target_resistance < 0:
        raise ValueError("target resistance cannot be negative")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(f"post-routing DD coverage requires a DD build; got role={getattr(build, 'Role', '')!r}")

    priorities = _priority_entries(tuple(args.priority or ()), build=build)
    priority_list = AbilityPriorityList(
        character_name=_character_name(build),
        build_name=str(getattr(build, "BuildName", "") or "").strip(),
        role=str(getattr(build, "Role", "") or "Unspecified").strip(),
        entries=priorities,
    )

    generated = RotationDDCrossBarGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=True,
            ability_priorities=priorities,
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="saved-build-post-routing",
        plan=generated.plan,
        refresh_leads=(),
        action_claims=(),
    )

    windows = tuple(_parse_target_window(raw) for raw in tuple(args.off_balance_window or ()))
    target_state_known = bool(args.target_state_known or windows)
    target_state_resolver = (
        RotationExplicitTargetCombatStateScheduleService(windows)
        if target_state_known
        else None
    )
    impact_evidence = tuple(
        parse_explicit_impact_anchor(raw)
        for raw in tuple(args.impact_anchor or ())
    )
    activation_anchor_resolver = build_explicit_activation_anchor_resolver(
        plan=candidate.plan,
        evidence=impact_evidence,
    )

    provider = _action_damage_provider(
        build=build,
        database_path=Path(args.database),
        builds_path=Path(args.builds),
        target_resistance=target_resistance,
        plan=candidate.plan,
        target_state_resolver=target_state_resolver,
        activation_anchor_resolver=activation_anchor_resolver,
    )
    audit = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    ).audit(candidate)
    triage = RotationDDWholePlanDamageBlockerTriageService().classify(audit)

    waits = sum(1 for action in candidate.plan.actions if action.kind.value == "wait")
    swaps = sum(1 for action in candidate.plan.actions if action.kind.value == "bar_swap")
    skills = sum(1 for action in candidate.plan.actions if action.kind.value == "skill")
    coverage = (
        100.0 * audit.resolved_damage_actions / audit.total_damage_actions
        if audit.total_damage_actions
        else 100.0
    )

    print("=" * 72)
    print(" PHASE 13 DD POST-ROUTING WHOLE-PLAN DAMAGE COVERAGE")
    print("=" * 72)
    print(f"Character:           {_character_name(build) or 'unnamed'}")
    print(f"Build:               {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:            {duration:g}s")
    print(f"Target resistance:   {target_resistance:g}")
    print(f"Final skill actions: {skills}")
    print(f"Final bar swaps:     {swaps}")
    print(f"Final waits:         {waits}")
    print(f"Damage actions:      {audit.total_damage_actions}")
    print(f"Resolved actions:    {audit.resolved_damage_actions}")
    print(f"Unresolved actions:  {audit.unresolved_damage_actions}")
    print(f"Coverage:            {coverage:.1f}%")
    print(f"Complete:            {audit.complete}")
    print()

    _print_triage_section("ACTIONABLE BLOCKERS", triage.actionable)
    _print_triage_section("RUNTIME-INPUT BLOCKERS", triage.runtime_input_required)
    _print_triage_section("PARKED-EVIDENCE BLOCKERS", triage.parked_evidence)

    print("INTERPRETATION")
    print("--------------")
    if triage.actionable:
        print("Actionable canonical damage blockers remain on the final routed production plan.")
    elif triage.runtime_input_required:
        print("No actionable damage-engineering blocker remains; exact runtime evidence is still required for some actions.")
    else:
        print("No actionable or runtime-input blocker remains on the final routed production plan.")
    if triage.parked_evidence:
        print("Parked evidence rows remain intentionally unresolved and should not trigger invented mechanics.")
    print("This audit does not rewrite scheduler policy or convert unknown damage to zero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
