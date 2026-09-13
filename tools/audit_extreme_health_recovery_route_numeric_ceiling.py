from __future__ import annotations

"""Score proof-reduced Health Recovery class-route ceilings without whole-record search."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_health_recovery_class_route_ceiling_service import (
    ExtremeHealthRecoveryClassRouteCeilingService,
)
from services.extreme_health_recovery_class_route_signature_service import (
    ExtremeHealthRecoveryClassRouteSignatureService,
)
from services.skill_choice_service import load_skill_choices


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _soldier_slot_ceiling(database: Path):
    rows = [
        row
        for row in load_skill_choices(database)
        if _norm(row.get("skill_line")) == "soldier of apocrypha"
        and int(row.get("is_player") or 0) == 1
        and int(row.get("is_passive") or 0) == 0
    ]
    regular: dict[int, str] = {}
    ultimate: dict[int, str] = {}
    for row in rows:
        base_id = int(row.get("base_ability_id") or row.get("ability_id") or 0)
        if base_id <= 0:
            continue
        target = ultimate if int(row.get("base_mechanic") or 0) == 8 else regular
        target.setdefault(base_id, str(row.get("name") or "<unnamed>"))

    regular_slots = min(5, len(regular))
    ultimate_slots = min(1, len(ultimate))
    return regular_slots + ultimate_slots, regular, ultimate


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    slot_ceiling, regular, ultimate = _soldier_slot_ceiling(database)
    routes = ExtremeHealClassRouteService().all_routes()
    signatures = ExtremeHealthRecoveryClassRouteSignatureService.build(routes)
    ceilings = ExtremeHealthRecoveryClassRouteCeilingService.build(
        signatures,
        wellspring_slot_ceiling=slot_ceiling,
    )

    print("EXTREME HEALTH RECOVERY CLASS ROUTE NUMERIC CEILING")
    print(f"database={database}")
    print("mode=reduced_signature_class_ceiling_not_whole_record_scoring")
    print()
    print("WELLSPRING SLOT CEILING")
    print(f"soldier_regular_base_families={len(regular)}")
    print(f"soldier_ultimate_base_families={len(ultimate)}")
    print(f"regular_bar_slots_available={min(5, len(regular))}")
    print(f"ultimate_bar_slots_available={min(1, len(ultimate))}")
    print(f"wellspring_slot_ceiling={slot_ceiling}")
    print(f"wellspring_flat_ceiling={slot_ceiling * 81.0:.3f}")
    for base_id, name in sorted(regular.items(), key=lambda item: (item[1].casefold(), item[0])):
        print(f"  regular: base_id={base_id} name={name!r}")
    for base_id, name in sorted(ultimate.items(), key=lambda item: (item[1].casefold(), item[0])):
        print(f"  ultimate: base_id={base_id} name={name!r}")

    print()
    print("ROUTE SIGNATURE CEILINGS")
    ordered = sorted(
        ceilings.rows,
        key=lambda row: (
            row.class_flat_ceiling is None,
            -(row.class_flat_ceiling or 0.0),
            row.signature.relevant_skill_lines,
            row.signature.class_mastery or "",
        ),
    )
    for row in ordered:
        print(
            f"  lines={row.signature.relevant_skill_lines!r} "
            f"mastery={row.signature.class_mastery or '<none>'} "
            f"class_flat_ceiling={row.class_flat_ceiling!r} "
            f"wellspring_slots={row.wellspring_slots} complete={row.score_complete}"
        )
        for item in row.unresolved:
            print(f"    unresolved: {item}")

    best = ceilings.best_complete
    print()
    if best is None:
        print("best_complete_signature=<none>")
    else:
        print(f"best_complete_signature={best.signature.identity!r}")
        print(f"best_complete_class_flat_ceiling={best.class_flat_ceiling:.3f}")
    print(f"complete_signature_rows={len(ceilings.complete_rows)}")
    print(f"unresolved_signature_rows={len(ceilings.unresolved_rows)}")
    for row in ceilings.unresolved_rows:
        print(
            f"  blocker: lines={row.signature.relevant_skill_lines!r} "
            f"mastery={row.signature.class_mastery or '<none>'}: "
            + "; ".join(row.unresolved)
        )

    numeric_route_dominance_proven = not ceilings.unresolved_rows and best is not None
    print(f"numeric_route_dominance_proven={numeric_route_dominance_proven}")
    if not numeric_route_dominance_proven:
        print("NEXT_STEP=close the remaining Class Mastery ceiling(s), then compare runtime compatibility of the best complete route")
        return 2
    print("NEXT_STEP=prove runtime compatibility of the dominant class route with shared recovery maxima")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
