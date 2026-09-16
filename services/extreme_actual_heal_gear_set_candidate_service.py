from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

from minmax.build_candidate import BuildCandidate
from minmax.gear_set_repository import GearSetRepository
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


_SOULSHINE_BLOCKER = re.compile(
    r"^Soulshine \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Activating an ability with a cast or channel time grants you\s*"
    r"(?:\d[\d,]*\s*-\s*)?369\s+Weapon and Spell Damage for\s*5 seconds\.?$",
    re.IGNORECASE | re.DOTALL,
)
_POWERFUL_ASSAULT_BLOCKER = re.compile(
    r"^Powerful Assault \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"When you cast an Assault ability while in combat, you and up to 5 group members within 12 meters gain\s*"
    r"(?:\d[\d,]*\s*-\s*)?307\s+Weapon and Spell Damage for\s*15 seconds\.?$",
    re.IGNORECASE | re.DOTALL,
)
_VOIDCALLER_BLOCKER = re.compile(
    r"^Voidcaller \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"When you take damage, your Weapon and Spell Damage is increased by\s*"
    r"(?:\d[\d,]*\s*-\s*)?24\s*for\s*5 seconds, stacking up to\s*20 times\.\s*"
    r"This effect can occur once every half second\.\s*"
    r"Upon reaching 20 stacks, the duration is doubled but can no longer be refreshed\.?$",
    re.IGNORECASE | re.DOTALL,
)
_CAMONNA_TONG_BLOCKER = re.compile(
    r"^Camonna Tong \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"When you kill a monster and gain Experience Points, gain 1 Weapon and Spell Damage for every 50 Experience Points the monster is worth for 30 seconds\.\s*"
    r"This bonus can stack up to a maximum of\s*(?:\d[\d,]*\s*-\s*)?540\s*Weapon and Spell Damage\.\s*"
    r"This item set is not affected by Experience Point boosting effects\.?$",
    re.IGNORECASE | re.DOTALL,
)
_RAVAGER_BLOCKER = re.compile(
    r"^Ravager \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Each time you attempt to reduce the target's Physical or Spell Resistance, you gain a stack of Ravager for 5 seconds, "
    r"increasing your Weapon and Spell Damage by\s*(?:\d[\d,]*\s*-\s*)?146\.\s*"
    r"You can gain a stack every 1 second\.\s*At 4 stacks, the duration doubles but cannot be refreshed\.?$",
    re.IGNORECASE | re.DOTALL,
)
_LIGHT_SPEAKER_BLOCKER = re.compile(
    r"^Light Speaker \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Adds\s*(?:\d[\d,]*\s*-\s*)?600\s+Weapon and Spell Damage to your Restoration Staff abilities\.?$",
    re.IGNORECASE | re.DOTALL,
)
_INNATE_AXIOM_BLOCKER = re.compile(
    r"^Innate Axiom \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Adds\s*(?:\d[\d,]*\s*-\s*)?400\s+Weapon and Spell Damage to your Class abilities\.?$",
    re.IGNORECASE | re.DOTALL,
)


class ExtremeActualHealGearSetCandidateService:
    """Materialize reviewed ordinary five-piece set mutations for actual-heal search.

    Authoritative H1 search is exhaustive across the reviewed ordinary five-piece
    universe. Admission remains fail-closed across the complete H1 objective screen.
    Candidate-scoped sets may enter the denominator once their condition is resolved
    from the actual selected heal during canonical evaluation.
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

    @staticmethod
    def _h1_review(row):
        review = ExtremeActualHealGearConditionRelevanceService.review(row)
        objective = str(row.objective_key or "").strip().casefold()
        blockers = tuple(str(value) for value in row.unresolved)
        set_name = str(row.set_name or "").strip().casefold()
        reviewed_blocker = {
            "soulshine": _SOULSHINE_BLOCKER,
            "powerful assault": _POWERFUL_ASSAULT_BLOCKER,
            "voidcaller": _VOIDCALLER_BLOCKER,
            "camonna tong": _CAMONNA_TONG_BLOCKER,
            "ravager": _RAVAGER_BLOCKER,
            "light speaker": _LIGHT_SPEAKER_BLOCKER,
            "innate axiom": _INNATE_AXIOM_BLOCKER,
        }.get(set_name)
        if (
            reviewed_blocker is not None
            and objective in {"spell_damage", "weapon_damage"}
            and blockers
            and all(reviewed_blocker.fullmatch(blocker) for blocker in blockers)
        ):
            return replace(
                review,
                h1_mechanic_complete=True,
                h1_positive_modifier_proven=True,
                ignored_blockers=blockers,
                remaining_blockers=(),
            )
        return review

    @classmethod
    def _h1_mechanic_complete(cls, row) -> bool:
        return cls._h1_review(row).h1_mechanic_complete

    @classmethod
    def _h1_positive(cls, row) -> bool:
        review = cls._h1_review(row)
        return bool(row.reviewed_delta > 0 or review.h1_positive_modifier_proven)

    def candidate_set_names(self, *, per_objective: int | None = None) -> tuple[str, ...]:
        names: list[str] = []
        seen: set[str] = set()
        limit = None if per_objective is None else max(1, int(per_objective))
        rows_by_objective = {
            objective: ExtremeGearSetObjectiveService.candidates_for_objective(self.repository, objective)
            for objective in self.OBJECTIVES
        }
        unresolved_set_ids = {
            int(row.set_id)
            for rows in rows_by_objective.values()
            for row in rows
            if not self._h1_mechanic_complete(row)
        }
        for objective in self.OBJECTIVES:
            accepted = 0
            for row in rows_by_objective[objective]:
                gear_set = self.repository.get_set_by_id(row.set_id)
                if gear_set is None:
                    continue
                useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(self.repository, gear_set)
                if useful < 5 or int(row.set_id) in unresolved_set_ids or not self._h1_mechanic_complete(row) or not self._h1_positive(row):
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
            before = {slot: str(build.Armor[slot].get("Set", "") or "") for slot in self.BODY_SLOTS[:5]}
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
