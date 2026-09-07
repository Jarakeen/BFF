from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.runtime_healer_wait_decision_provider import RuntimeHealerWaitDecisionProvider


def _skill(time_seconds: float, name: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Synthetic Warden",
        build_name="RO Healer",
        duration_seconds=31.0,
        actions=(
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(3.0, "Action A"),
            _skill(24.0, "Long Buff"),
            _skill(26.0, "Long Buff"),
            _skill(28.0, "Long Buff"),
            _skill(29.0, "Action B"),
            _skill(30.0, "Action C"),
            _skill(31.0, "Action D"),
        ),
    )


def _rules() -> tuple[RotationRecastRule, ...]:
    return (
        RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),
        RotationRecastRule("Action A", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action B", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action C", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action D", duration_seconds=60.0, bar="front"),
    )


def _ro_incentive() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified synthetic RO evidence",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
    )


def main() -> int:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_ro_incentive(),),
        required_window_seconds=1.8,
    )
    refined = DurationAwareRotationScheduler().refine(
        _plan(),
        _rules(),
        wait_decision=provider,
    )

    print("=" * 64)
    print(" PHASE 13 SYNTHETIC RO HEALER ROTATION AUDIT")
    print("=" * 64)
    print("Scenario: repeated duration skill creates legal RO heavy windows")
    print("RO recurrence: 22s from completed qualifying heavy")
    print("Heavy channel: 1.8s")
    print()
    print("FINAL TIMELINE")
    print("--------------")
    for action in refined.actions:
        label = action.name or ""
        print(
            f"{action.time_seconds:>5.1f}s  "
            f"{action.kind.value:<12}  "
            f"{(action.bar or 'unknown'):<5}  {label}"
        )

    print()
    print("REQUIRED HEAVY RUNTIME STATE")
    print("----------------------------")
    if provider.runtime_states:
        for state in provider.runtime_states:
            print(
                f"{state.incentive_name} | {state.bar} | "
                f"last qualifying trigger={state.last_trigger_seconds:g}s"
            )
    else:
        print("none")

    print()
    print("UNRESOLVED / DISPLACEMENT TRACE")
    print("-------------------------------")
    if refined.unresolved:
        for item in refined.unresolved:
            print(item)
    else:
        print("none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
