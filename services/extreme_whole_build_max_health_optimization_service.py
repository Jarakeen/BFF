from __future__ import annotations

from pathlib import Path

from minmax.build_candidate import BuildCandidate
from models.build_model import PlayerBuild
from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)
from services.extreme_complete_optimization_service import (
    ExtremeCompleteOptimizationService,
    ExtremeObjective,
)


class ExtremeWholeBuildMaxHealthOptimizationService(ExtremeCompleteOptimizationService):
    """Extend canonical Max Health search across reviewed whole-build packages.

    ``ExtremeCompleteOptimizationService`` remains authoritative for canonical
    stat evaluation and the ordinary sheet mutation families. This subtype adds
    the same reviewed race/set/package materialization surfaces used by Actual
    Heal so Max-Health-scaling mechanics are not limited to sheet-only discovery.

    Every emitted build is still rescored through the parent canonical context;
    package tooltip deltas are discovery hints only and never the final score.
    """

    SEARCH_SCOPE = (
        *ExtremeCompleteOptimizationService.SEARCH_SCOPE,
        "race replacement",
        "reviewed ordinary five-piece set replacement",
        "reviewed legal five-piece + two-piece monster package",
        "reviewed legal five-piece + five-piece package",
        "reviewed legal five-piece + five-piece + ring mythic package",
        "reviewed legal five-piece + five-piece + non-ring mythic package",
    )
    OMITTED_SCOPE = (
        "class/subclass route change",
        "skill-bar passive/proc search",
        "group-only buffs",
        "runtime conditional stacks/procs",
        "arena-weapon replacement where Max Health value does not originate from the arena package itself",
    )

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        builds_path: Path | None = None,
        gear_set_candidates: ExtremeActualHealGearSetCandidateService | None = None,
        monster_packages: ExtremeActualHealMonsterPackageService | None = None,
        double_five_packages: ExtremeActualHealDoubleFivePackageService | None = None,
        mythic_packages: ExtremeActualHealMythicPackageService | None = None,
        non_ring_mythic_packages: ExtremeActualHealNonRingMythicPackageService | None = None,
    ) -> None:
        super().__init__(database_path=database_path, builds_path=builds_path)
        resolved_path = self.database_path
        self.gear_set_candidates = (
            gear_set_candidates
            if gear_set_candidates is not None
            else ExtremeActualHealGearSetCandidateService(resolved_path)
        )
        self.monster_packages = (
            monster_packages
            if monster_packages is not None
            else ExtremeActualHealMonsterPackageService(resolved_path)
        )
        self.double_five_packages = (
            double_five_packages
            if double_five_packages is not None
            else ExtremeActualHealDoubleFivePackageService(resolved_path)
        )
        self.mythic_packages = (
            mythic_packages
            if mythic_packages is not None
            else ExtremeActualHealMythicPackageService(resolved_path)
        )
        self.non_ring_mythic_packages = (
            non_ring_mythic_packages
            if non_ring_mythic_packages is not None
            else ExtremeActualHealNonRingMythicPackageService(resolved_path)
        )

    def _candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        objective: ExtremeObjective,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        candidates = list(
            super()._candidates(
                baseline_build,
                objective=objective,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
        )
        if objective.key != "max_health":
            return tuple(candidates)

        candidates.extend(
            self._race_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
        )
        candidates.extend(
            self.gear_set_candidates.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
        )
        candidates.extend(
            self.monster_packages.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
        )
        candidates.extend(
            self.double_five_packages.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
        )
        candidates.extend(
            self.mythic_packages.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                active_bar="front",
            )
        )
        candidates.extend(
            self.non_ring_mythic_packages.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                active_bar="front",
            )
        )
        return tuple(candidates)

    def optimize(
        self,
        baseline_build: PlayerBuild,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ):
        # Package legality depends on the selected active weapon. Preserve that
        # bar through candidate generation for the duration of this optimization.
        self._active_bar_for_package_search = str(active_bar or "front")
        try:
            return super().optimize(
                baseline_build,
                objective_key,
                active_bar=active_bar,
                max_passes=max_passes,
            )
        finally:
            self._active_bar_for_package_search = "front"

    def _race_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        before = str(baseline_build.Race or "").strip()
        result: list[BuildCandidate] = []
        for race in self.race_repository.list_races():
            name = str(race.name or "").strip()
            if not name or name.casefold() == before.casefold():
                continue
            build = PlayerBuild.from_dict(baseline_build.to_dict())
            build.Race = name
            result.append(
                self._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"whole-max-health-race:{name}",
                    path="Race",
                    before=before,
                    after=name,
                    source="extreme:whole-build-max-health:race",
                )
            )
        return tuple(result)
