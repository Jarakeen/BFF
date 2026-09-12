from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.resource_costs import ResourceType
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDWholePlanDamageCoverageAuditService,
)
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generate_dd_role_evidence_support import (
    RotationGenerateDDCanonicalWeaponAttackProviderFactory,
    RotationGenerateDDRoleEvidenceSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


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


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _action_damage_provider(*, build, database_path: Path, target_resistance: float):
    support = RotationGenerateDDRoleEvidenceSupport(
        database_path=database_path,
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
    role_output = role_evidence.plan_evidence_provider.role_output_evidence_provider
    provider = getattr(role_output, "action_damage_evidence_provider", None)
    if provider is None:
        raise RuntimeError("DD role evidence did not expose its canonical action-damage provider")
    return provider


def _sorted_blockers(audit):
    return tuple(
        sorted(
            audit.blockers,
            key=lambda item: (
                -item.occurrence_count,
                item.action_kind.value,
                (item.action_name or "").casefold(),
                item.reason.casefold(),
            ),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one real saved DD rotation and count whole-plan canonical damage "
            "coverage using the same action-damage provider as Generate projected DPS."
        )
    )
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "eso.db")
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--target-resistance", type=float, required=True)
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

    duration = float(args.duration)
    if duration <= 0.0:
        raise ValueError("duration must be positive")
    target_resistance = float(args.target_resistance)
    if target_resistance < 0.0:
        raise ValueError("target resistance cannot be negative")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in {"dd", "dps", "damage", "damage dealer", "damage_dealer"}:
        raise ValueError(
            "whole-plan DD coverage audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

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
    provider = _action_damage_provider(
        build=build,
        database_path=Path(args.database),
        target_resistance=target_resistance,
    )
    audit = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    ).audit(candidate)

    print("=" * 72)
    print(" PHASE 13 DD WHOLE-PLAN DAMAGE COVERAGE AUDIT")
    print("=" * 72)
    print(f"Character:             {_character_name(build) or 'unnamed'}")
    print(f"Build:                 {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Role:                  {getattr(build, 'Role', '') or 'unresolved'}")
    print(f"Duration:              {duration:g}s")
    print(f"Target resistance:     {target_resistance:g}")
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
    print()

    print("BLOCKERS BY OCCURRENCE")
    print("----------------------")
    blockers = _sorted_blockers(audit)
    if not blockers:
        print("none")
    else:
        for index, blocker in enumerate(blockers, start=1):
            label = blocker.action_kind.value
            if blocker.action_name:
                label += f" {blocker.action_name}"
            print(f"{index:2d}. {blocker.occurrence_count:3d}x | {label}")
            print(f"    {blocker.reason}")
            print(
                "    occurrences: "
                + ", ".join(
                    f"{time_seconds:g}s #{sequence}"
                    for time_seconds, sequence in blocker.occurrences
                )
            )
    print()

    print("PLAN-LEVEL UNRESOLVED")
    print("---------------------")
    if candidate.plan.unresolved:
        for item in candidate.plan.unresolved:
            print(item)
    else:
        print("none")
    print()
    print(
        "Interpretation: blocker frequency identifies the highest-yield missing DD "
        "damage evidence for this exact generated saved-build plan. It does not promote "
        "observational mechanics or treat unknown damage as zero."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
