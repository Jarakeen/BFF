from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_gear_search_completeness_audit_service import (
    ExtremeGearSearchCompletenessAuditService,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_resource_active_skill_coverage_audit_service import (
    ExtremeResourceActiveSkillCoverageAuditService,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_equipment_trait_projection_coverage_service import (
    ExtremeResourceEquipmentTraitProjectionCoverageService,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_resource_runtime_projection_coverage_service import (
    ExtremeResourceRuntimeProjectionCoverageService,
)
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
_COMPLETE_BOUNDARY = (
    "All dynamic axes in this record's declared search universe are covered by "
    "searched or proof-owned denominator evidence."
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Extreme max-resource closure. By default this performs a fast proof "
            "preflight over the independent denominator services. Use --full only when "
            "you intentionally want the complete combinatorial final-record search."
        )
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the exhaustive published-record search after the fast proof preflight.",
    )
    return parser


def _fast_preflight(database: Path) -> bool:
    print("EXTREME RESOURCE RECORD CLOSURE PREFLIGHT")
    print(f"Database: {database}")
    print("Mode: FAST PROOF PREFLIGHT")

    universe = ExtremeGlobalSearchUniverseService(database).build()
    structural_complete = bool(universe.structural_denominator_proven)
    print(f"structural_denominator_proven={structural_complete}")

    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()

    complete = structural_complete
    for objective in _OBJECTIVES:
        print(f"\n{objective.upper()}")

        relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
            objective,
            breakpoints,
        )
        gear = ExtremeGearSearchCompletenessAuditService.build(
            topology=topology,
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=relevance,
        )
        gear_complete = bool(gear.denominator_proven)

        trait_glyph_service = ExtremeArmorResourceTraitGlyphStateService(database)
        armor = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
            objective,
            trait_glyph_service=trait_glyph_service,
        ).build(objective)
        armor_complete = bool(armor.denominator_proven)

        passives = ExtremeResourcePassiveCoverageAuditService(database).build(objective)
        passive_complete = bool(passives.projection_complete)

        champion_points = ExtremeResourceChampionPointStateService(database).build(objective)
        cp_complete = bool(
            champion_points.denominator_proven and not champion_points.unresolved
        )

        active_skills = ExtremeResourceActiveSkillCoverageAuditService(database).build(objective)
        active_skill_complete = bool(active_skills.projection_complete)

        equipment = ExtremeResourceEquipmentTraitProjectionCoverageService(database).build(
            objective
        )
        equipment_complete = bool(equipment.projection_complete)

        runtime = ExtremeResourceRuntimeProjectionCoverageService(database).build(objective)
        runtime_complete = bool(runtime.projection_complete)

        objective_complete = all(
            (
                structural_complete,
                gear_complete,
                armor_complete,
                passive_complete,
                cp_complete,
                active_skill_complete,
                equipment_complete,
                runtime_complete,
            )
        )

        print(f"gear_denominator_proven={gear_complete}")
        print(f"resource_armor_denominator_proven={armor_complete}")
        print(f"passive_projection_complete={passive_complete}")
        print(f"champion_point_projection_complete={cp_complete}")
        print(f"active_skill_projection_complete={active_skill_complete}")
        print(f"equipment_trait_projection_complete={equipment_complete}")
        print(f"runtime_projection_complete={runtime_complete}")
        print(f"preflight_complete={objective_complete}")

        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *gear.unresolved,
                    *armor.unresolved,
                    *passives.unresolved,
                    *champion_points.unresolved,
                    *active_skills.unresolved,
                    *equipment.unresolved,
                    *runtime.unresolved,
                )
                if str(item)
            )
        )
        if unresolved:
            print("UNRESOLVED")
            for item in unresolved:
                print(f"  {item}")

        complete = complete and objective_complete and not unresolved

    print("\nNOTE")
    print(
        "Fast preflight proves the independent denominator prerequisites without "
        "enumerating the full named-gear realization search. Use --full for the "
        "authoritative end-to-end published-record closure run."
    )
    return complete


def _full_record_audit(database: Path) -> bool:
    print("\nEXTREME RESOURCE RECORD CLOSURE")
    print("Mode: FULL EXHAUSTIVE RECORD SEARCH")
    print("This intentionally executes the complete combinatorial record search.")

    service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        database_path=database
    )
    complete = True

    for objective in _OBJECTIVES:
        print(f"\n{objective.upper()}: starting exhaustive record search...", flush=True)
        record = service.record(objective)
        boundary = next(
            (
                row
                for row in record.explanation
                if row.startswith("Residual unproven search axes:")
                or row == _COMPLETE_BOUNDARY
            ),
            "",
        )
        objective_complete = bool(
            record.proof_status is ExtremeRecordProofStatus.PROVEN
            and record.search_coverage.complete
            and record.globally_proven
            and not record.search_coverage.omitted
            and not record.unresolved
            and boundary == _COMPLETE_BOUNDARY
        )

        print(f"raw_value={record.raw_value}")
        print(f"proof_status={record.proof_status.value}")
        print(f"coverage_denominator_proven={record.search_coverage.denominator_proven}")
        print(f"coverage_complete={record.search_coverage.complete}")
        print(f"globally_proven={record.globally_proven}")
        print(f"omitted={', '.join(record.search_coverage.omitted)}")
        print(f"unresolved={', '.join(record.unresolved)}")
        print(f"residual_boundary={boundary}")
        print(f"record_closure_complete={objective_complete}")
        complete = complete and objective_complete

    return complete


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    preflight_complete = _fast_preflight(database)
    if not preflight_complete:
        return 2

    if not args.full:
        return 0

    return 0 if _full_record_audit(database) else 2


if __name__ == "__main__":
    raise SystemExit(main())
