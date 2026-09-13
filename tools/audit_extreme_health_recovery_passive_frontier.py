from __future__ import annotations

"""Inventory every canonical player passive relevant to Extreme Health Recovery.

This is a proof-frontier audit, not a scorer. It uses the shared passive projector
for static/contextual semantics and a narrow Health Recovery special classifier for
non-static grammars that the generic projector deliberately leaves unresolved.
"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_health_recovery_passive_special_branch_service import (
    ExtremeHealthRecoveryPassiveSpecialBranchService,
)
from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService

OBJECTIVE = "health_recovery"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    universe = ExtremeSkillUniverseService(database)
    passives = tuple(row for row in universe.all_player_skills() if row.is_passive)
    projections = tuple(ExtremePassiveProjectionService.project(row) for row in passives)

    direct = []
    contextual = []
    special = []
    unresolved = []
    by_domain: dict[str, list] = defaultdict(list)

    for projection in projections:
        row = projection.passive
        contributions = tuple(
            contribution
            for contribution in projection.contributions
            if contribution.objective_key == OBJECTIVE
        )
        text = f"{row.name} {row.description}".casefold()
        recovery_text = "health recovery" in text or (
            "health" in text and "magicka" in text and "stamina recovery" in text
        )

        if contributions:
            direct.append((projection, contributions))
            by_domain[row.domain.value].append((projection, contributions))
            continue
        if recovery_text and projection.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED:
            contextual.append(projection)
            by_domain[row.domain.value].append((projection, ()))
            continue
        if recovery_text and projection.status is ExtremePassiveProjectionStatus.UNRESOLVED:
            branch = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(row)
            if branch is None:
                unresolved.append(projection)
            else:
                special.append(branch)
            by_domain[row.domain.value].append((projection, ()))

    status_counts = Counter(row.status.value for row in projections)

    print("EXTREME HEALTH RECOVERY PASSIVE FRONTIER")
    print(f"database={database}")
    print("mode=canonical_passive_inventory_plus_semantic_special_classification")
    print(f"player_passives_reviewed={len(passives)}")
    print(
        "projection_status_counts="
        + ", ".join(f"{key}:{value}" for key, value in sorted(status_counts.items()))
    )
    print(f"direct_health_recovery_passives={len(direct)}")
    print(f"context_required_health_recovery_passives={len(contextual)}")
    print(f"special_health_recovery_passives={len(special)}")
    print(f"unresolved_health_recovery_passives={len(unresolved)}")
    print()

    print("DIRECT HEALTH RECOVERY PASSIVES")
    for projection, contributions in sorted(
        direct,
        key=lambda item: (
            item[0].passive.domain.value,
            item[0].passive.class_type.casefold(),
            item[0].passive.skill_line.casefold(),
            item[0].passive.name.casefold(),
        ),
    ):
        row = projection.passive
        values = ", ".join(
            f"flat={item.flat:g} percent_of_reference={item.percent_of_reference:g}"
            for item in contributions
        )
        print(
            f"  domain={row.domain.value} class={row.class_type or '<shared>'} "
            f"line={row.skill_line!r} passive={row.name!r} {values}"
        )

    print()
    print("CONTEXT-REQUIRED HEALTH RECOVERY PASSIVES")
    for projection in sorted(
        contextual,
        key=lambda item: (
            item.passive.domain.value,
            item.passive.class_type.casefold(),
            item.passive.skill_line.casefold(),
            item.passive.name.casefold(),
        ),
    ):
        row = projection.passive
        print(
            f"  domain={row.domain.value} class={row.class_type or '<shared>'} "
            f"line={row.skill_line!r} passive={row.name!r} conditions={projection.conditions!r}"
        )
        for message in projection.unresolved:
            print(f"    context: {message}")

    print()
    print("SEMANTIC SPECIAL HEALTH RECOVERY PASSIVES")
    for branch in sorted(
        special,
        key=lambda item: (
            item.passive.domain.value,
            item.passive.class_type.casefold(),
            item.passive.skill_line.casefold(),
            item.passive.name.casefold(),
        ),
    ):
        row = branch.passive
        print(
            f"  domain={row.domain.value} class={row.class_type or '<shared>'} "
            f"line={row.skill_line!r} passive={row.name!r} kind={branch.kind.value} "
            f"can_raise_self={branch.can_raise_self} flat_ceiling={branch.flat_ceiling!r} "
            f"percent_ceiling={branch.percent_ceiling!r} condition={branch.condition or '<none>'}"
        )

    print()
    print("UNRESOLVED HEALTH RECOVERY PASSIVES")
    for projection in sorted(
        unresolved,
        key=lambda item: (
            item.passive.domain.value,
            item.passive.class_type.casefold(),
            item.passive.skill_line.casefold(),
            item.passive.name.casefold(),
        ),
    ):
        row = projection.passive
        print(
            f"  domain={row.domain.value} class={row.class_type or '<shared>'} "
            f"line={row.skill_line!r} passive={row.name!r} description={row.description!r}"
        )
        for message in projection.unresolved:
            print(f"    unresolved: {message}")

    print()
    print("RELEVANT PASSIVES BY DOMAIN")
    for domain, rows in sorted(by_domain.items()):
        print(f"  {domain}={len(rows)}")

    denominator_classified = not unresolved
    print()
    print(f"health_recovery_passive_semantic_denominator_classified={denominator_classified}")
    if unresolved:
        print("NEXT_STEP=close unresolved Health Recovery passive grammars before route dominance proof")
        return 2
    print("NEXT_STEP=prove race/class/shared passive ownership and reduce legal class routes by Health Recovery signature")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
