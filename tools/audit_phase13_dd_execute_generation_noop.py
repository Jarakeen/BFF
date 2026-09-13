from __future__ import annotations

"""Prove that execute-aware DD Generate is a no-op without proven execute evidence.

This read-only audit runs the same saved DD build through the production DD generation
wrapper twice: once without execute runtime context and once with an explicit 20%-Health
target snapshot.  Corpsebuster currently has no positive canonical execute candidate
on its ordinary bars, so the two generated plans must be identical and the canonical
action-damage provider must never be called.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_state_snapshot import CombatantSnapshot, CombatStateSnapshot
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from tools.audit_phase13_dd_priority_schedule import _priority_entries
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_execute_generation_context import RotationDDExecuteGenerationContext
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


class _MustNotEvaluateDamage:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate_action(self, *, candidate, action) -> RotationActionDamageEvidence:
        self.calls += 1
        raise AssertionError(
            "canonical damage provider was called even though Corpsebuster has no "
            "proven execute candidate"
        )


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _snapshot(time_seconds: float) -> CombatStateSnapshot:
    return CombatStateSnapshot(
        time_seconds=float(time_seconds),
        player=CombatantSnapshot(
            identity="player",
            current_health=100.0,
            maximum_health=100.0,
        ),
        targets=(
            CombatantSnapshot(
                identity="boss",
                current_health=20.0,
                maximum_health=100.0,
            ),
        ),
    )


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
        help="Rank every occupied ordinary saved-bar slot.",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("duration must be positive")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD execute no-op audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    priorities = _priority_entries(tuple(args.priority or ()), build=build)
    request = RotationGenerationRequest(
        duration_seconds=duration,
        weave_light_attacks=True,
        ability_priorities=priorities,
    )

    baseline = RotationDDCrossBarGenerationSupport(
        base=RotationGenerationSupport(),
    ).generate_with_evidence(build=build, request=request)

    damage_provider = _MustNotEvaluateDamage()

    def execute_context_resolver(*, build, request, generated, routed_plan):
        return RotationDDExecuteGenerationContext(
            snapshot_resolver=_snapshot,
            target_identity="boss",
            action_damage_provider=damage_provider,
        )

    execute_aware = RotationDDCrossBarGenerationSupport(
        base=RotationGenerationSupport(),
        execute_context_resolver=execute_context_resolver,
    ).generate_with_evidence(build=build, request=request)

    same_actions = baseline.plan.actions == execute_aware.plan.actions
    same_assumptions = baseline.plan.assumptions == execute_aware.plan.assumptions
    same_unresolved = baseline.plan.unresolved == execute_aware.plan.unresolved
    same_plan = baseline.plan == execute_aware.plan

    print("=" * 72)
    print(" PHASE 13 DD EXECUTE GENERATION NEGATIVE-CONTROL AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print("Execute target Health: 20%")
    print()
    print("PLAN COMPARISON")
    print("---------------")
    print(f"baseline_actions={len(baseline.plan.actions)}")
    print(f"execute_aware_actions={len(execute_aware.plan.actions)}")
    print(f"actions_identical={same_actions}")
    print(f"assumptions_identical={same_assumptions}")
    print(f"unresolved_identical={same_unresolved}")
    print(f"plan_identical={same_plan}")
    print(f"damage_provider_calls={damage_provider.calls}")
    print()

    if not same_plan:
        print("RESULT=FAIL: execute context changed a build with no proven execute candidate")
        return 1
    if damage_provider.calls != 0:
        print("RESULT=FAIL: execute comparison ran without a proven execute candidate")
        return 1

    print(
        "RESULT=PASS: explicit low-Health execute context leaves Corpsebuster unchanged "
        "because no slotted ordinary skill has positive canonical execute evidence"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
