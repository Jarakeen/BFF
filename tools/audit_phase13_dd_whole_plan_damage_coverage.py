from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.resource_costs import ResourceType
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_dd_output_context_relevance_service import (
    RotationDDOutputContextRelevanceService,
)
from services.rotation_dd_whole_plan_damage_blocker_triage_service import (
    RotationDDWholePlanDamageBlockerTriageService,
)
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDWholePlanDamageCoverageAuditService,
)
from services.rotation_explicit_target_combat_state_schedule_service import (
    RotationExplicitTargetCombatStateScheduleService,
    RotationTargetCombatStateWindow,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from tools.dd_audit_activation_anchor_support import (
    build_explicit_activation_anchor_resolver,
    parse_explicit_impact_anchor,
)
from tools.dd_audit_runtime_state_support import (
    build_plan_attacker_runtime_state_resolver,
)
from ui.rotation_generate_dd_role_evidence_support import (
    RotationGenerateDDCanonicalWeaponAttackProviderFactory,
    RotationGenerateDDRoleEvidenceSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


@dataclass(frozen=True)
class _DDAuditEvidenceBundle:
    """Minimal DD composition inputs used only by this read-only coverage audit.

    RotationGenerateDDRoleEvidenceSupport requires target resistance, content type,
    and a resource label while composing its canonical plan-evidence adapter. The
    coverage audit consumes only the resulting action-damage provider, so no sustain,
    encounter, or recovery facts are fabricated here.
    """

    target_resistance: float
    resource: ResourceType = ResourceType.MAGICKA
    content_type: str = "audit"


@dataclass(frozen=True)
class _StaticPrerequisiteGap:
    reason: str
    bars: tuple[str, ...]


class _DDAuditStaticContextService:
    """Apply the canonical DD relevance gate consistently inside audit composition.

    The shared static context intentionally retains diagnostics needed by other roles.
    This read-only adapter removes only diagnostics already classified as ambient for
    modeled DD damage. Unknown or offensive diagnostics remain unresolved and fail
    closed. The same delegate is reused for runtime context rebuilds so the audit does
    not pass its preflight gate and then trip over a stricter duplicate gate in
    ``RotationGenerateDDRoleEvidenceSupport``.
    """

    def __init__(self, delegate: RotationStaticBuildContextService) -> None:
        self.delegate = delegate
        self.relevance_service = RotationDDOutputContextRelevanceService()

    def resolve(self, player_build, **kwargs):
        result = self.delegate.resolve(player_build, **kwargs)
        relevance = self.relevance_service.classify(result.unresolved)
        if not result.progression.resolved or relevance.relevant:
            return replace(result, unresolved=tuple(relevance.relevant))
        return replace(result, unresolved=())


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _saved_dd_builds(path: Path) -> tuple[tuple[str, str, str], ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, str]] = []
    for member in payload.get("Members", []):
        role = str(member.get("Role", "") or "").strip()
        if role.casefold() not in _DD_ROLE_KEYS:
            continue
        character = str(
            member.get("CharacterName", "")
            or member.get("Name", "")
            or member.get("Gamertag", "")
            or ""
        ).strip()
        build_name = str(member.get("BuildName", "") or "").strip()
        rows.append((character, build_name, role))
    return tuple(sorted(rows, key=lambda item: (item[0].casefold(), item[1].casefold())))


def _parse_target_window(
    raw: str,
    *,
    buff_name: str = "Off Balance",
) -> RotationTargetCombatStateWindow:
    text = str(raw or "").strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"target state window must use START:END seconds, got {raw!r}"
        )
    try:
        start = float(parts[0])
        end = float(parts[1])
    except ValueError as exc:
        raise ValueError(
            f"target state window must use numeric START:END seconds, got {raw!r}"
        ) from exc
    return RotationTargetCombatStateWindow(start, end, (buff_name,))


def _group_static_prerequisite_gaps(
    unresolved: tuple[str, ...],
) -> tuple[_StaticPrerequisiteGap, ...]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for raw in unresolved:
        message = str(raw or "").strip()
        if not message:
            continue
        bar = "build"
        reason = message
        for candidate in ("front", "back"):
            prefix = f"{candidate} static context: "
            if message.casefold().startswith(prefix):
                bar = candidate
                reason = message[len(prefix):].strip()
                break
        grouped[reason].add(bar)

    order = {"front": 0, "back": 1, "build": 2}
    result = [
        _StaticPrerequisiteGap(
            reason=reason,
            bars=tuple(sorted(bars, key=lambda value: (order.get(value, 99), value))),
        )
        for reason, bars in grouped.items()
    ]
    return tuple(
        sorted(
            result,
            key=lambda item: (-len(item.bars), item.reason.casefold()),
        )
    )


def _action_damage_provider(
    *,
    build,
    database_path: Path,
    builds_path: Path,
    target_resistance: float,
    plan=None,
    target_state_resolver=None,
    activation_anchor_resolver=None,
):
    static_context_service = _DDAuditStaticContextService(
        RotationStaticBuildContextService(
            database_path=database_path,
            builds_path=builds_path,
        )
    )
    support = RotationGenerateDDRoleEvidenceSupport(
        database_path=database_path,
        static_context_service=static_context_service,  # type: ignore[arg-type]
        weapon_attack_provider_factory=(
            RotationGenerateDDCanonicalWeaponAttackProviderFactory(
                database_path=database_path,
            )
        ),
    )
    role_evidence = support.compose(
        player_build=build,
        evidence_bundle=_DDAuditEvidenceBundle(
            target_resistance=float(target_resistance),
        ),  # type: ignore[arg-type]
    )
    plan_evidence = role_evidence.plan_evidence_provider
    attacker_state_resolver = (
        build_plan_attacker_runtime_state_resolver(build=build, plan=plan)
        if plan is not None
        else None
    )
    if (
        target_state_resolver is not None
        or attacker_state_resolver is not None
        or activation_anchor_resolver is not None
    ):
        if plan is None:
            raise ValueError("runtime DD audit provider requires a rotation plan")
        binder = getattr(plan_evidence, "for_stabilized_snapshot", None)
        if not callable(binder):
            raise RuntimeError("DD plan evidence does not expose runtime snapshot binding")
        plan_evidence = binder(
            SimpleNamespace(
                plan=plan,
                runtime_combat_state_resolver=attacker_state_resolver,
                runtime_target_combat_state_resolver=target_state_resolver,
                runtime_target_resistance_resolver=None,
                runtime_activation_anchor_resolver=activation_anchor_resolver,
            )
        )
    role_output = plan_evidence.role_output_evidence_provider
    provider = getattr(role_output, "action_damage_evidence_provider", None)
    if provider is None:
        raise RuntimeError("DD role evidence did not expose its canonical action-damage provider")
    return provider


def _sorted_triage(items):
    return tuple(
        sorted(
            items,
            key=lambda item: (
                -item.blocker.occurrence_count,
                item.blocker.action_kind.value,
                (item.blocker.action_name or "").casefold(),
                item.blocker.reason.casefold(),
            ),
        )
    )


def _print_triage_section(title: str, items) -> None:
    print(title)
    print("-" * len(title))
    rows = _sorted_triage(items)
    if not rows:
        print("none")
        print()
        return
    for index, item in enumerate(rows, start=1):
        blocker = item.blocker
        label = blocker.action_kind.value
        if blocker.action_name:
            label += f" {blocker.action_name}"
        print(f"{index:2d}. {blocker.occurrence_count:3d}x | {label}")
        print(f"    {blocker.reason}")
        if item.disposition_reason:
            print(f"    disposition: {item.disposition_reason}")
        print(
            "    occurrences: "
            + ", ".join(
                f"{time_seconds:g}s #{sequence}"
                for time_seconds, sequence in blocker.occurrences
            )
        )
    print()


def _print_static_prerequisite_report(
    *,
    build,
    gaps: tuple[_StaticPrerequisiteGap, ...],
    ambient: tuple[str, ...] = (),
) -> None:
    print("=" * 72)
    print(" PHASE 13 DD STATIC DAMAGE PREREQUISITE AUDIT")
    print("=" * 72)
    print(f"Character:             {_character_name(build) or 'unnamed'}")
    print(f"Build:                 {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Role:                  {getattr(build, 'Role', '') or 'unresolved'}")
    print("Boundary:              action-damage coverage not attempted until DD-relevant static state resolves")
    print()
    print("DD-RELEVANT PREREQUISITE GAPS")
    print("-----------------------------")
    if gaps:
        for index, gap in enumerate(gaps, start=1):
            bars = ", ".join(gap.bars)
            print(f"{index:2d}. {len(gap.bars)} bar(s) | {bars}")
            print(f"    {gap.reason}")
    else:
        print("none")
    print()
    print(f"Ambient non-damage diagnostics excluded from this gate: {len(ambient)}")
    print()
    print(
        "Interpretation: only unresolved facts that can still affect modeled DD damage "
        "remain blocking here. Known movement-speed, harvesting, max-health-only, and "
        "healing-taken-only diagnostics are ambient for this output. Unknown mechanics "
        "still fail closed, and no unresolved offensive input is treated as zero."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one real saved DD rotation and count whole-plan canonical damage "
            "coverage using the same action-damage provider as Generate projected DPS."
        )
    )
    parser.add_argument("--character")
    parser.add_argument("--build")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "eso.db")
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument(
        "--list-dd-builds",
        action="store_true",
        help="List saved DD/DPS builds from builds.json and exit without generating a plan.",
    )
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--target-resistance", type=float)
    parser.add_argument(
        "--target-state-known",
        action="store_true",
        help=(
            "Treat target CombatState as authoritative even outside named windows. "
            "With no windows this means the target is known not to have scheduled buffs."
        ),
    )
    parser.add_argument(
        "--off-balance-window",
        action="append",
        default=[],
        metavar="START:END",
        help=(
            "Add one authoritative half-open Off Balance window [START, END) in seconds. "
            "May be supplied multiple times and implies --target-state-known."
        ),
    )
    parser.add_argument(
        "--impact-anchor",
        action="append",
        default=[],
        metavar="SKILL:ACTION_TIME:SEQUENCE:IMPACT_TIME",
        help=(
            "Add exact caller-owned impact timing for one final-plan skill action. "
            "May be repeated. No impact timing is inferred when omitted."
        ),
    )
    parser.add_argument("--ultimate-bar", choices=("front", "back"))
    parser.add_argument("--starting-ultimate", type=float, default=0.0)
    parser.add_argument(
        "--use-scheduled-attacks-for-ultimate",
        action="store_true",
        help="Use scheduled light/heavy attacks for the existing Ultimate-generation model.",
    )
    parser.add_argument(
        "--no-weave",
        action="store_true",
        help="Disable the normal saved-build light-attack weaving generation path.",
    )
    args = parser.parse_args()

    if args.list_dd_builds:
        builds = _saved_dd_builds(Path(args.builds))
        print("=" * 72)
        print(" SAVED DD BUILDS ELIGIBLE FOR WHOLE-PLAN DAMAGE COVERAGE AUDIT")
        print("=" * 72)
        if not builds:
            print("none")
        else:
            for character, build_name, role in builds:
                print(
                    f"{character or '(unnamed character)'} | "
                    f"{build_name or '(unnamed build)'} | {role}"
                )
        return 0

    if not str(args.build or "").strip():
        parser.error("--build is required unless --list-dd-builds is used")
    if args.target_resistance is None:
        parser.error("--target-resistance is required unless --list-dd-builds is used")

    duration = float(args.duration)
    if duration <= 0.0:
        raise ValueError("duration must be positive")
    target_resistance = float(args.target_resistance)
    if target_resistance < 0.0:
        raise ValueError("target resistance cannot be negative")

    off_balance_windows = tuple(
        _parse_target_window(raw)
        for raw in tuple(args.off_balance_window or ())
    )
    target_state_known = bool(args.target_state_known or off_balance_windows)
    target_state_resolver = (
        RotationExplicitTargetCombatStateScheduleService(off_balance_windows)
        if target_state_known
        else None
    )
    impact_anchor_evidence = tuple(
        parse_explicit_impact_anchor(raw)
        for raw in tuple(args.impact_anchor or ())
    )

    builds_path = Path(args.builds)
    database_path = Path(args.database)
    build = _load_build(builds_path, args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "whole-plan DD coverage audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    static_context_service = RotationStaticBuildContextService(
        database_path=database_path,
        builds_path=builds_path,
    )
    static_context = static_context_service.resolve(build)
    relevance = RotationDDOutputContextRelevanceService().classify(
        static_context.unresolved
    )
    if not static_context.progression.resolved or relevance.relevant:
        relevant = tuple(static_context.progression.unresolved) + tuple(relevance.relevant)
        gaps = _group_static_prerequisite_gaps(tuple(dict.fromkeys(relevant)))
        _print_static_prerequisite_report(
            build=build,
            gaps=gaps,
            ambient=tuple(relevance.ambient),
        )
        return 2

    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=not bool(args.no_weave),
            ultimate_bar=str(args.ultimate_bar or ""),
            starting_ultimate=float(args.starting_ultimate),
            use_scheduled_combat_attacks_for_ultimate=bool(
                args.use_scheduled_attacks_for_ultimate
            ),
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="saved-build-generated",
        plan=generated.plan,
        refresh_leads=(),
        action_claims=(),
    )
    activation_anchor_resolver = build_explicit_activation_anchor_resolver(
        plan=candidate.plan,
        evidence=impact_anchor_evidence,
    )
    provider = _action_damage_provider(
        build=build,
        database_path=database_path,
        builds_path=builds_path,
        target_resistance=target_resistance,
        plan=candidate.plan,
        target_state_resolver=target_state_resolver,
        activation_anchor_resolver=activation_anchor_resolver,
    )
    audit = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    ).audit(candidate)
    triage = RotationDDWholePlanDamageBlockerTriageService().classify(audit)

    print("=" * 72)
    print(" PHASE 13 DD WHOLE-PLAN DAMAGE COVERAGE AUDIT")
    print("=" * 72)
    print(f"Character:             {_character_name(build) or 'unnamed'}")
    print(f"Build:                 {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Role:                  {getattr(build, 'Role', '') or 'unresolved'}")
    print(f"Duration:              {duration:g}s")
    print(f"Target resistance:     {target_resistance:g}")
    print("Attacker CombatState:  plan-derived reviewed persistent toggles")
    print(
        "Runtime anchors:       "
        + (
            f"{len(impact_anchor_evidence)} explicit impact anchor(s)"
            if impact_anchor_evidence
            else "none (non-cast anchors remain unresolved)"
        )
    )
    print(
        "Target CombatState:    "
        + ("explicit schedule" if target_state_known else "unresolved")
    )
    if target_state_known:
        if off_balance_windows:
            print(
                "Off Balance windows:   "
                + ", ".join(
                    f"{window.start_seconds:g}:{window.end_seconds:g}s"
                    for window in off_balance_windows
                )
            )
        else:
            print("Off Balance windows:   none (authoritative)")
    print(f"Light-attack weaving:  {'off' if args.no_weave else 'on'}")
    print(f"Ultimate bar:          {args.ultimate_bar or 'not selected'}")
    print("Boundary:              read-only coverage audit; unresolved damage remains unknown")
    print()

    print("COVERAGE")
    print("--------")
    print(f"Damage actions:        {audit.total_damage_actions}")
    print(f"Resolved actions:      {audit.resolved_damage_actions}")
    print(f"Unresolved actions:    {audit.unresolved_damage_actions}")
    if audit.total_damage_actions:
        ratio = audit.resolved_damage_actions / audit.total_damage_actions
        print(f"Resolved coverage:     {ratio:.1%}")
    print(f"Actionable blockers:   {len(triage.actionable)}")
    print(f"Parked blockers:       {len(triage.parked)}")
    print()

    _print_triage_section("ACTIONABLE BLOCKERS", triage.actionable)
    _print_triage_section("PARKED EVIDENCE BLOCKERS", triage.parked)

    print("PLAN-LEVEL UNRESOLVED")
    print("---------------------")
    if candidate.plan.unresolved:
        for item in candidate.plan.unresolved:
            print(item)
    else:
        print("none")
    print()
    print(
        "Interpretation: actionable blockers identify the highest-yield missing DD "
        "damage evidence for this exact generated saved-build plan. Parked evidence "
        "blockers remain unresolved and continue to fail closed, but are separated so "
        "known exhausted research lanes do not masquerade as fresh work."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
