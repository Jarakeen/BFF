from __future__ import annotations

"""Inventory canonical passives that can affect Extreme Magicka Recovery."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService

OBJECTIVE = "magicka_recovery"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _mentions_recovery(text: str) -> bool:
    value = " ".join(str(text or "").casefold().split())
    return "magicka recovery" in value or (
        "health" in value and "magicka" in value and "stamina recovery" in value
    )


def main() -> int:
    database = Path(_parser().parse_args().database)
    passives = tuple(
        row for row in ExtremeSkillUniverseService(database).all_player_skills() if row.is_passive
    )
    projections = tuple(ExtremePassiveProjectionService.project(row) for row in passives)

    direct = []
    contextual = []
    special = []
    unresolved = []
    by_domain: dict[str, list[str]] = defaultdict(list)

    for projection in projections:
        row = projection.passive
        contributions = tuple(
            item for item in projection.contributions if item.objective_key == OBJECTIVE
        )
        relevant_text = _mentions_recovery(f"{row.name} {row.description}")
        if contributions:
            direct.append((projection, contributions))
            by_domain[row.domain.value].append(row.name)
            continue
        if not relevant_text:
            continue
        if projection.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED:
            contextual.append(projection)
            by_domain[row.domain.value].append(row.name)
            continue
        branch = ExtremeRecoveryPassiveSpecialBranchService.classify(row, OBJECTIVE)
        if branch is not None:
            special.append(branch)
            by_domain[row.domain.value].append(row.name)
            continue
        if projection.status is ExtremePassiveProjectionStatus.UNRESOLVED:
            unresolved.append(projection)
            by_domain[row.domain.value].append(row.name)

    counts = Counter(row.status.value for row in projections)
    print("EXTREME MAGICKA RECOVERY PASSIVE FRONTIER")
    print(f"database={database}")
    print(f"player_passives_reviewed={len(passives)}")
    print("projection_status_counts=" + ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())))
    print(f"direct_magicka_recovery_passives={len(direct)}")
    print(f"context_required_magicka_recovery_passives={len(contextual)}")
    print(f"special_magicka_recovery_passives={len(special)}")
    print(f"unresolved_magicka_recovery_passives={len(unresolved)}")

    print("\nDIRECT")
    for projection, contributions in direct:
        row = projection.passive
        values = ", ".join(
            f"flat={item.flat:g} percent_of_reference={item.percent_of_reference:g}"
            for item in contributions
        )
        print(f"  domain={row.domain.value} class={row.class_type or '<shared>'} line={row.skill_line!r} passive={row.name!r} {values}")

    print("\nCONTEXT REQUIRED")
    for projection in contextual:
        row = projection.passive
        print(f"  domain={row.domain.value} class={row.class_type or '<shared>'} line={row.skill_line!r} passive={row.name!r} conditions={projection.conditions!r}")

    print("\nSEMANTIC SPECIAL")
    for branch in special:
        row = branch.passive
        print(
            f"  domain={row.domain.value} class={row.class_type or '<shared>'} line={row.skill_line!r} "
            f"passive={row.name!r} kind={branch.kind.value} flat_ceiling={branch.flat_ceiling!r} "
            f"percent_ceiling={branch.percent_ceiling!r} condition={branch.condition or '<none>'}"
        )

    print("\nUNRESOLVED")
    for projection in unresolved:
        row = projection.passive
        print(f"  domain={row.domain.value} class={row.class_type or '<shared>'} line={row.skill_line!r} passive={row.name!r} description={row.description!r}")

    print("\nRELEVANT BY DOMAIN")
    for domain, names in sorted(by_domain.items()):
        print(f"  {domain}={len(names)}")

    closed = not unresolved
    print(f"\nmagicka_recovery_passive_semantic_denominator_classified={closed}")
    if closed:
        print("NEXT_STEP=score legal class/subclass routes from the classified Magicka Recovery passive set")
        return 0
    print("NEXT_STEP=close only the listed unresolved Magicka Recovery passive grammars")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
