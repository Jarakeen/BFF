from __future__ import annotations

"""List every canonical passive branch that can still raise Extreme Magicka Recovery.

This is a read-only denominator audit. It classifies the full passive universe through
ExtremeRecoveryPassiveSpecialBranchService and reports route compatibility with the
promoted Animal Companions / Curative Runeforms / Shadow subclass route.
"""

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService

OBJECTIVE = "magicka_recovery"
PROMOTED_CLASS_LINES = frozenset({"animal_companions", "curative_runeforms", "shadow"})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _key(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _is_class_domain(row) -> bool:
    return "class" in str(getattr(row.domain, "value", row.domain)).casefold()


def main() -> int:
    database = Path(_parser().parse_args().database)
    universe = ExtremeSkillUniverseService(database)
    rows = []
    unresolved = []

    for passive in universe.passives():
        branch = ExtremeRecoveryPassiveSpecialBranchService.classify(passive, OBJECTIVE)
        if branch is None or not branch.can_raise_self:
            continue

        line_key = _key(passive.skill_line)
        class_route_compatible = (not _is_class_domain(passive)) or line_key in PROMOTED_CLASS_LINES
        numeric_ceiling_proven = (
            branch.kind in {
                ExtremeRecoveryPassiveBranchKind.STATIC_PERCENT,
                ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT,
            }
            and branch.percent_ceiling is not None
        ) or (
            branch.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT
            and branch.flat_ceiling is not None
        )
        if branch.kind is ExtremeRecoveryPassiveBranchKind.SCALING_RECOVERY:
            numeric_ceiling_proven = False

        rows.append(
            (
                str(getattr(passive.domain, "value", passive.domain)),
                str(passive.skill_line),
                str(passive.name),
                branch.kind.value,
                branch.flat_ceiling,
                branch.percent_ceiling,
                branch.condition,
                class_route_compatible,
                numeric_ceiling_proven,
                " ".join(str(passive.description or "").split()),
            )
        )

    rows.sort(key=lambda row: (not row[7], row[0].casefold(), row[1].casefold(), row[2].casefold()))

    print("EXTREME MAGICKA RECOVERY REMAINING CONTEXTUAL PASSIVE AUDIT")
    print(f"database={database}")
    print(f"promoted_class_lines={tuple(sorted(PROMOTED_CLASS_LINES))!r}")
    print(f"positive_branch_count={len(rows)}")
    print()

    compatible = []
    incompatible = []
    scaling = []
    for row in rows:
        domain, line, name, kind, flat, percent, condition, route_ok, numeric_ok, description = row
        print(
            f"PASSIVE domain={domain!r} line={line!r} name={name!r} kind={kind!r} "
            f"flat_ceiling={flat!r} percent_ceiling={percent!r} condition={condition!r} "
            f"promoted_route_compatible={route_ok} numeric_ceiling_proven={numeric_ok}"
        )
        print(f"  description={description!r}")
        if route_ok:
            compatible.append(name)
        else:
            incompatible.append(name)
        if kind == ExtremeRecoveryPassiveBranchKind.SCALING_RECOVERY.value:
            scaling.append(name)

    print()
    print("SUMMARY")
    print(f"route_compatible_positive_passives={tuple(compatible)!r}")
    print(f"route_incompatible_positive_passives={tuple(incompatible)!r}")
    print(f"scaling_passives_requiring_external_ceiling={tuple(scaling)!r}")
    print(f"audit_unresolved_count={len(unresolved)}")
    print("NEXT_STEP=close only route-compatible conditional/scaling branches, then compose final Recovery snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
