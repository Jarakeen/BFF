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
    reviewed gear-set objective layer to discover mechanic-complete candidate sets,
    then writes each set onto real body slots so the whole build can be reevaluated
    by the canonical context factory.

    Authoritative H1 search is exhaustive across the reviewed ordinary five-piece
    universe. ``per_objective`` is optional and exists only for focused callers or
    tests that deliberately want a bounded sample; production callers omit it.

    Candidate discovery includes generic healing/critical/power stats plus all
    three maximum-resource families because legal heals may scale from Health,
    Magicka, or Stamina. Final usefulness is still decided only after the real
    candidate build is reevaluated through canonical heal math.

    Admission is fail-closed across the complete H1 objective screen. A set with
    unresolved active mechanics for any H1 discovery objective cannot re-enter the
    authoritative pool merely because a different objective has a reviewed positive
    contribution. This preserves one set-level mechanic-completeness boundary.

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

    def candidate_set_names(
        self,
        *,
        per_objective: int | None = None,
    ) -> tuple[str, ...]:
        names: list[str] = []
        seen: set[str] = set()
        limit = None if per_objective is None else max(1, int(per_objective))

        rows_by_objective = {
            objective: ExtremeGearSetObjectiveService.candidates_for_objective(
                self.repository,
                objective,
            )
            for objective in self.OBJECTIVES
        }
        unresolved_set_ids = {
            int(row.set_id)
            for rows in rows_by_objective.values()
            for row in rows
            if not row.mechanic_complete
        }

        for objective in self.OBJECTIVES:
            accepted = 0
            for row in rows_by_objective[objective]:
                gear_set = self.repository.get_set_by_id(row.set_id)
                if gear_set is None:
                    continue
                useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
                    self.repository,
                    gear_set,
                )
                if (
                    useful < 5
                    or int(row.set_id) in unresolved_set_ids
                    or not row.mechanic_complete
                    or row.reviewed_delta <= 0
                ):
                    continue
                key = row.set_name.casefold()
                if key not in seen:
                    seen.add(key)
                    names.append(row.set_name)
                accepted += 1
                if limit is not None and accepted >= limit:
                    break
        return tuple(names)

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        per_objective: int | None = None,
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
