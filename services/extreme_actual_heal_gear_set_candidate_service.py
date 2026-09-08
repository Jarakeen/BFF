from __future__ import annotations

from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.gear_set_repository import GearSetRepository
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class ExtremeActualHealGearSetCandidateService:
    """Materialize reviewed ordinary five-piece set mutations for actual-heal search.

    This service does not rank set tooltip deltas as final answers. It uses the
    reviewed gear-set objective layer only to build a bounded candidate pool, then
    writes the set onto real body slots so the whole build can be reevaluated by
    the canonical context factory.

    Candidate discovery includes generic healing/critical/power stats plus all
    three maximum-resource families because legal heals may scale from Health,
    Magicka, or Stamina. Final usefulness is still decided only after the real
    candidate build is reevaluated through canonical heal math.

    Monster sets, mythics, arena weapons, and mixed 5+2+1 packages are intentionally
    outside this first body-set tranche because they require slot-family legality,
    not merely a set name and piece count.
    """

    OBJECTIVES = (
        "healing_done",
        "critical_healing",
        "spell_damage",
        "weapon_damage",
        "max_health",
        "max_magicka",
        "max_stamina",
    )
    BODY_SLOTS = ("Chest", "Legs", "Head", "Shoulders", "Hands", "Waist", "Feet")

    def __init__(self, database_path: str | Path) -> None:
        self.repository = GearSetRepository(database_path)

    def candidate_set_names(self, *, per_objective: int = 12) -> tuple[str, ...]:
        names: list[str] = []
        seen: set[str] = set()
        limit = max(1, int(per_objective))
        for objective in self.OBJECTIVES:
            accepted = 0
            for row in ExtremeGearSetObjectiveService.candidates_for_objective(
                self.repository,
                objective,
            ):
                gear_set = self.repository.get_set_by_id(row.set_id)
                if gear_set is None:
                    continue
                useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
                    self.repository,
                    gear_set,
                )
                if useful < 5 or not row.mechanic_complete or row.reviewed_delta <= 0:
                    continue
                key = row.set_name.casefold()
                if key not in seen:
                    seen.add(key)
                    names.append(row.set_name)
                accepted += 1
                if accepted >= limit:
                    break
        return tuple(names)

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        per_objective: int = 12,
    ) -> tuple[BuildCandidate, ...]:
        result: list[BuildCandidate] = []
        current_primary = {
            str(entry.get("Set", "") or "").strip().casefold()
            for entry in baseline_build.Armor.values()
            if str(entry.get("Set", "") or "").strip()
        }

        for set_name in self.candidate_set_names(per_objective=per_objective):
            if set_name.casefold() in current_primary:
                continue
            build = PlayerBuild.from_dict(baseline_build.to_dict())
            before = {
                slot: str(build.Armor[slot].get("Set", "") or "")
                for slot in self.BODY_SLOTS[:5]
            }
            for slot in self.BODY_SLOTS[:5]:
                build.Armor[slot]["Set"] = set_name

            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-five-piece:{set_name}",
                    path="Armor.PrimaryFivePieceSet",
                    before=before,
                    after={slot: set_name for slot in self.BODY_SLOTS[:5]},
                    source="extreme:actual-heal:gear-set",
                )
            )
        return tuple(result)
