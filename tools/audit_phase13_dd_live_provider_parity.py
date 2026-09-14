from __future__ import annotations

"""Compare legacy and live DD role-evidence providers on one saved DD build.

The Rotation Builder now installs ``RotationGenerateDDTargetHealthRoleEvidenceSupport``.
When no reviewed periodic target-Health semantics or Health trajectory are active, its
canonical action-damage evidence must remain identical to the pre-target-Health DD
support. This read-only audit proves that additive production adoption did not change
ordinary saved-build DD output merely by installing the new wrapper.

Audit composition uses the same DD relevance-filtered static-context adapter as the
whole-plan damage coverage audit. Ambient non-damage diagnostics therefore do not
prevent the parity comparison, while unknown or DD-relevant offensive diagnostics
remain unresolved and fail closed.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.resource_costs import ResourceType
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from tools.audit_phase13_dd_whole_plan_damage_coverage import _DDAuditStaticContextService
from tools.dd_audit_priority_fixture_support import resolve_audit_priorities
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generate_dd_role_evidence_support import (
    RotationGenerateDDCanonicalWeaponAttackProviderFactory,
    RotationGenerateDDRoleEvidenceSupport,
)
from ui.rotation_generate_dd_target_health_role_evidence_support import (
    RotationGenerateDDTargetHealthRoleEvidenceSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


class _Bundle:
    target_resistance = 18200.0
    resource = ResourceType.MAGICKA
    content_type = "audit"
    target_health_trajectory = None
    encounter_id = "audit-target"


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _provider(support, *, build):
    role_evidence = support.compose(player_build=build, evidence_bundle=_Bundle())
    plan_evidence = role_evidence.plan_evidence_provider
    role_output = plan_evidence.role_output_evidence_provider
    provider = getattr(role_output, "action_damage_evidence_provider", None)
    if provider is None:
        raise RuntimeError("DD role evidence did not expose action-damage provider")
    return provider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "eso.db")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="BAR:SLOT:PRIORITY",
        help=(
            "Rank every occupied ordinary saved-bar slot. If omitted entirely, this "
            "regression audit uses a deterministic audit-only saved-slot fixture."
        ),
    )
    args = parser.parse_args()

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD provider parity audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    duration = float(args.duration)
    if duration <= 0.0:
        raise ValueError("duration must be positive")
    priorities, used_priority_fixture = resolve_audit_priorities(
        tuple(args.priority or ()),
        build=build,
    )
    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=True,
            ability_priorities=priorities,
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="provider-parity",
        plan=generated.plan,
        refresh_leads=(),
    )

    static_context_service = _DDAuditStaticContextService(
        RotationStaticBuildContextService(
            database_path=Path(args.database),
            builds_path=Path(args.builds),
        )
    )
    weapon_factory = RotationGenerateDDCanonicalWeaponAttackProviderFactory(
        database_path=Path(args.database),
    )
    legacy = RotationGenerateDDRoleEvidenceSupport(
        database_path=Path(args.database),
        static_context_service=static_context_service,  # type: ignore[arg-type]
        weapon_attack_provider_factory=weapon_factory,
    )
    live = RotationGenerateDDTargetHealthRoleEvidenceSupport(
        database_path=Path(args.database),
        static_context_service=static_context_service,  # type: ignore[arg-type]
        weapon_attack_provider_factory=weapon_factory,
    )

    legacy_provider = _provider(legacy, build=build)
    live_provider = _provider(live, build=build)

    mismatches = []
    compared = 0
    for action in candidate.plan.actions:
        if action.kind.value not in {"skill", "light_attack", "heavy_attack", "ultimate"}:
            continue
        compared += 1
        left = legacy_provider.evaluate_action(candidate=candidate, action=action)
        right = live_provider.evaluate_action(candidate=candidate, action=action)
        if left != right:
            mismatches.append((action, left, right))

    print("=" * 72)
    print(" PHASE 13 DD LIVE PROVIDER PARITY AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(
        "Priority source: "
        + (
            "deterministic audit-only saved-slot fixture"
            if used_priority_fixture
            else "explicit --priority input"
        )
    )
    print("Static context: DD relevance-filtered audit composition")
    print(f"Actions compared: {compared}")
    print(f"Mismatches:       {len(mismatches)}")
    print()

    if mismatches:
        for action, legacy_evidence, live_evidence in mismatches[:10]:
            print(f"{action.time_seconds:g}s #{action.sequence} {action.kind.value} {action.name or ''}")
            print(f"  legacy={legacy_evidence}")
            print(f"  live=  {live_evidence}")
        print("RESULT=FAIL: live target-Health support changed DD evidence without active Health semantics")
        return 1

    print("RESULT=PASS: live target-Health DD support is evidence-identical when target-Health mechanics are inactive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
