from __future__ import annotations

"""Audit runtime compatibility of the dominant Health Recovery route and gear frontier."""

import argparse
from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.gear_set_repository import GearSetRepository
from minmax.ultimate_generation_sources import (
    CombatAttackUltimateGenerationSource,
    HeroismTier,
    HeroismUltimateGenerationSource,
    HeroismWindow,
)
from services.champion_point_loadout_service import ChampionPointLoadoutCandidate
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)
from services.extreme_health_recovery_champion_point_branch_service import (
    ExtremeHealthRecoveryChampionPointBranchService,
)
from services.extreme_health_recovery_runtime_compatibility_service import (
    ExtremeHealthRecoveryCompatibility,
    ExtremeHealthRecoveryRuntimeCompatibilityService,
    ExtremeHealthRecoveryRuntimeState,
)

OBJECTIVE = "health_recovery"
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _special_catalog(database: Path):
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    rows: list[tuple[str, int, str]] = []
    unresolved: list[str] = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            unresolved.append(str(item))
            continue
        rows.append((match.group("name"), int(match.group("count")), match.group("description")))
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(tuple(rows), objective_key=OBJECTIVE)
    return catalog, tuple(dict.fromkeys((*unresolved, *catalog.unresolved)))


def _selected_cp_candidates(database: Path):
    repository = ChampionPointStaticRepository(database)
    names = (
        "Strategic Reserve",
        "Peace of Mind",
        "Enlivening Overflow",
        "Sustained by Suffering",
        "Rejuvenation",
    )
    candidates: list[ChampionPointLoadoutCandidate] = []
    unresolved: list[str] = []
    for name in names:
        record = repository.get(name)
        if record is None:
            unresolved.append(f"selected CP record missing: {name}")
            continue
        if name == "Rejuvenation":
            row = ExtremeChampionPointObjectiveService.candidate_for_record(
                repository,
                record,
                OBJECTIVE,
            )
            if row.reviewed_delta is None:
                unresolved.extend(row.unresolved or (f"{name}: numeric ceiling missing",))
                continue
            ceiling = float(row.reviewed_delta)
            condition = None
        else:
            branch = ExtremeHealthRecoveryChampionPointBranchService.classify(record)
            if not branch.complete or branch.flat_ceiling is None:
                unresolved.extend(branch.unresolved or (f"{name}: branch incomplete",))
                continue
            ceiling = float(branch.flat_ceiling)
            condition = branch.condition
        candidates.append(
            ChampionPointLoadoutCandidate(
                name=name,
                discipline_index=record.discipline_index,
                flat_ceiling=ceiling,
                condition=condition,
            )
        )
    return tuple(candidates), tuple(unresolved)


def _reviewed_ultimate_generation(score_seconds: float):
    attacks = tuple(float(second) for second in range(25))
    base = CombatAttackUltimateGenerationSource().events(
        attack_times=attacks,
        duration_seconds=score_seconds,
    )
    heroism = HeroismUltimateGenerationSource().events(
        windows=(
            HeroismWindow(HeroismTier.MINOR, 0.0, score_seconds, source="Minor Heroism"),
            HeroismWindow(HeroismTier.MAJOR, 0.0, score_seconds, source="Major Heroism"),
        ),
        duration_seconds=score_seconds,
    )
    return tuple((*base, *heroism))


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    catalog, semantic_unresolved = _special_catalog(database)

    score_seconds = 24.999
    generation_events = _reviewed_ultimate_generation(score_seconds)
    state = ExtremeHealthRecoveryRuntimeState(
        score_seconds=score_seconds,
        ultimate_generation_events=generation_events,
        max_magicka=None,
    )
    cp_candidates, cp_discovery_unresolved = _selected_cp_candidates(database)
    assessments = ExtremeHealthRecoveryRuntimeCompatibilityService.build(
        catalog.positive_challengers,
        state,
    )
    counts = Counter(row.status.value for row in assessments)
    cp_assessments = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_points(
        cp_candidates,
        state,
    )
    cp_counts = Counter(row.status.value for row in cp_assessments)

    print("EXTREME HEALTH RECOVERY RUNTIME COMPATIBILITY")
    print(f"database={database}")
    print("mode=dominant_route_shared_state_plus_cp_and_special_branch_compatibility")
    print()
    print("DOMINANT ROUTE / SHARED STATE")
    print("race='Khajiit' racial_flat=90")
    print("class='Dragonknight' route=('draconic_power',) mastery='booming_voice'")
    print("class_flat_ceiling=1950")
    print(f"low_health_boundary={state.low_health_boundary}")
    print(f"booming_voice_window={state.booming_voice_window}")
    print(f"home_keeps={state.home_keeps}")
    print(f"continuous_attack_active={state.continuous_attack_active}")
    print(f"heavy_armor_pieces={state.heavy_armor_pieces}")
    print(f"major_fortitude_active={state.major_fortitude_active}")
    print(f"provisioning_kind={state.provisioning_kind!r}")
    print(f"dominant_shared_state_compatible={state.dominant_shared_state_compatible}")
    print()

    print("CHAMPION POINT RUNTIME COMPATIBILITY")
    print(f"selected_cp_candidates={len(cp_candidates)}")
    print(f"modeled_ultimate_generation={sum(event.amount for event in generation_events):.3f}")
    print("cp_status_counts=" + ", ".join(f"{key}:{value}" for key, value in sorted(cp_counts.items())))
    for row in cp_assessments:
        print(
            f"  {row.candidate.name} status={row.status.value} "
            f"flat_ceiling={row.candidate.flat_ceiling:.3f} reason={row.reason}"
        )
        if row.available_ultimate_at_score is not None:
            print(
                f"    available_ultimate_at_score={row.available_ultimate_at_score:.3f} "
                f"ultimate_shortfall={float(row.ultimate_shortfall or 0.0):.3f}"
            )
        if row.required_max_magicka is not None:
            print(f"    required_max_magicka={row.required_max_magicka:.3f}")
    print()

    print("SPECIAL GEAR COMPATIBILITY")
    print(f"positive_special_challengers={len(catalog.positive_challengers)}")
    print("status_counts=" + ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())))
    for row in assessments:
        branch = row.branch
        print(
            f"  {branch.set_name} {branch.piece_count}pc status={row.status.value} "
            f"flat={branch.flat_ceiling!r} percent={branch.percent_ceiling!r} "
            f"reason={row.reason}"
        )

    unresolved = list((*semantic_unresolved, *cp_discovery_unresolved))
    unresolved.extend(
        f"{row.candidate.name}: {row.reason}"
        for row in cp_assessments
        if row.status
        in {
            ExtremeHealthRecoveryCompatibility.RUNTIME_PROOF_REQUIRED,
            ExtremeHealthRecoveryCompatibility.INCOMPATIBLE,
        }
    )
    if not state.dominant_shared_state_compatible:
        unresolved.append("Dominant Dragonknight/shared runtime state is internally incompatible")
    print()
    print(f"runtime_compatibility_unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")

    if unresolved:
        print(
            "NEXT_STEP=close the exact Max Magicka requirement for Enlivening Overflow "
            "and the remaining Ultimate-generation gap for Strategic Reserve"
        )
        return 2
    print("runtime_compatibility_denominator_closed=True")
    print(
        "NEXT_STEP=score ordinary equipment/jewelry/CP and the compatible special branches; "
        "rescore Green Pact with food and keep search-state mutations separate"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
