from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.healer_ability_priority import HealerTagPriority
from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    resolve_healer_rotation_policy,
)
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind
from minmax.saved_build_rotation_timing_audit import audit_saved_build_rotation_timing
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_saved_build_recovery_threshold_sweep import minimum_timeline_point
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"

# Explicit audit policy for the current real DF Healer validation build.
# These annotations are intentionally diagnostic rather than universal production
# truth. The point of this audit is to test the existing healer-policy machinery
# against a real rotation before any default classification is exposed in the UI.
_DF_HEALER_AUDIT_TAGS: dict[str, tuple[HealerRotationTag, ...]] = {
    "Budding Seeds": (
        HealerRotationTag.BURST_PREPARATION,
        HealerRotationTag.SUSTAINED_HEALING,
    ),
    "Radiating Regeneration": (HealerRotationTag.SUSTAINED_HEALING,),
    "Combat Prayer": (HealerRotationTag.SUPPORT_MAINTENANCE,),
    "Illustrious Healing": (HealerRotationTag.SUSTAINED_HEALING,),
    "Energy Orb": (
        HealerRotationTag.SUSTAINED_HEALING,
        HealerRotationTag.SUPPORT_MAINTENANCE,
    ),
    "Winter's Revenge": (HealerRotationTag.SUPPORT_MAINTENANCE,),
    "Expansive Frost Cloak": (HealerRotationTag.SUPPORT_MAINTENANCE,),
    "Overflowing Altar": (HealerRotationTag.SUPPORT_MAINTENANCE,),
    "Elemental Susceptibility": (HealerRotationTag.SUPPORT_MAINTENANCE,),
    "Echoing Vigor": (HealerRotationTag.SUSTAINED_HEALING,),
}

_BASE_PRIORITIES = (
    HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
    HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 2),
    HealerTagPriority(HealerRotationTag.BURST_PREPARATION, 3),
    HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 4),
    HealerTagPriority(HealerRotationTag.MOVEMENT_UTILITY, 6),
    HealerTagPriority(HealerRotationTag.DISCRETIONARY_FILLER, 8),
)


def _audit_policy_set(build, *, database_path: Path):
    timing = audit_saved_build_rotation_timing(build, database_path=database_path)
    policies = []
    unclassified = []
    for item in timing.skills:
        if item.slot > 5:
            continue
        tags = _DF_HEALER_AUDIT_TAGS.get(item.skill_name)
        if tags is None:
            unclassified.append(f"{item.bar} slot {item.slot}: {item.skill_name}")
            continue
        policies.append(
            HealerSkillPolicy(
                bar=item.bar,
                slot=item.slot,
                skill_name=item.skill_name,
                tags=tags,
            )
        )
    if unclassified:
        raise ValueError(
            "DF Healer audit policy has no explicit classification for: "
            + "; ".join(unclassified)
        )
    return resolve_healer_rotation_policy(
        timing,
        tuple(policies),
        require_all_slotted=False,
    )


def _plan_metrics(*, build, plan, database_path: Path) -> dict[str, object]:
    sustain = RotationSustainService(database_path=database_path).evaluate(
        build=build,
        plan=plan,
        resource=ResourceType.MAGICKA,
    )
    timeline = sustain.run.timeline
    minimum_time, minimum_amount = minimum_timeline_point(timeline)
    unresolved = tuple(plan.unresolved)
    return {
        "waits": sum(action.kind is RotationActionKind.WAIT for action in plan.actions),
        "refresh_claims": sum(item.startswith("refresh obligation") for item in unresolved),
        "premature_waits": sum("scheduled wait instead" in item for item in unresolved),
        "displaced_beyond": sum("was displaced beyond" in item for item in unresolved),
        "minimum_time": minimum_time,
        "minimum_magicka": minimum_amount,
        "ending_magicka": timeline.ending_amount,
        "shortfall": timeline.total_shortfall,
        "unresolved": sustain.unresolved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare saved-slot-order rotation generation with an explicit audit-only "
            "healer priority policy for one real saved build."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--duration", type=float, default=60.0)
    args = parser.parse_args()

    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    database_path = Path(args.database)
    policy_set = _audit_policy_set(build, database_path=database_path)
    projection = HealerRotationPriorityService().project(
        policy_set=policy_set,
        base_priorities=_BASE_PRIORITIES,
    )

    generator = RotationGenerationSupport()
    baseline = generator.generate(
        build=build,
        request=RotationGenerationRequest(duration_seconds=float(args.duration)),
    )
    prioritized = generator.generate(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=float(args.duration),
            ability_priorities=projection.entries,
        ),
    )

    baseline_metrics = _plan_metrics(
        build=build,
        plan=baseline,
        database_path=database_path,
    )
    priority_metrics = _plan_metrics(
        build=build,
        plan=prioritized,
        database_path=database_path,
    )

    print("=" * 88)
    print(" PHASE 13 REAL HEALER PRIORITY COMPARISON")
    print("=" * 88)
    print(f"Character: {args.character}")
    print(f"Build:     {args.build}")
    print(f"Duration:  {float(args.duration):g}s")
    print(
        "Boundary:  audit-only explicit healer classifications; not a universal production policy"
    )
    print()

    print("PRIORITY ORDER")
    print("--------------")
    for entry in projection.entries:
        tags = _DF_HEALER_AUDIT_TAGS.get(entry.skill_name, ())
        rendered_tags = ", ".join(tag.value for tag in tags)
        print(
            f"{entry.priority:2d} | {entry.bar:5s} slot {entry.slot} | "
            f"{entry.skill_name} | {rendered_tags}"
        )
    print()

    print("METRIC                     | SAVED SLOT ORDER | HEALER PRIORITY | DELTA")
    print("---------------------------+------------------+-----------------+----------")
    for key, label in (
        ("refresh_claims", "Refresh claims"),
        ("premature_waits", "Premature-recast waits"),
        ("waits", "WAIT actions"),
        ("displaced_beyond", "Displaced beyond horizon"),
        ("minimum_magicka", "Minimum Magicka"),
        ("ending_magicka", "Ending Magicka"),
        ("shortfall", "Total shortfall"),
    ):
        before = int(baseline_metrics[key])
        after = int(priority_metrics[key])
        print(f"{label:27s}| {before:16d} | {after:15d} | {after - before:+8d}")

    print()
    print(
        "Minimum timing: "
        f"saved={float(baseline_metrics['minimum_time']):g}s, "
        f"priority={float(priority_metrics['minimum_time']):g}s"
    )
    print()
    print("Interpretation: fewer collisions/waits are useful only if healing/support obligations")
    print("remain protected. This audit compares scheduling behavior; it does not certify the")
    print("audit tag assignments as canonical healer policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
