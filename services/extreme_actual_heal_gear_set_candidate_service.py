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


_ARMOR_MASTER_BLOCKER = re.compile(
    r"^Armor Master \(5\): relevant percentage set effect requires "
    r"objective-specific stacking/reference review$",
    re.IGNORECASE,
)
_BASALT_BLOODED_WARRIOR_BLOCKER = re.compile(
    r"^Basalt-Blooded Warrior \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Casting an Earthen Heart ability grants you (?:a )?Rock Stance for\s*10 seconds\.\s*"
    r"While (?:you\s*are\s+)?on your Primary Weapon you gain Molten Stance, "
    r"granting you Major Heroism, generating\s*\d+(?:\.\d+)?\s*Ultimate every\s*"
    r"\d+(?:\.\d+)?\s*seconds\.\s*"
    r"While (?:you\s*are\s+)?on your Secondary Weapon you gain Obsidian Stance, "
    r"increasing your Healing Done and damage\s*shields by\s*14%\.\s*"
    r"Bar Swapping will swap your Stance automatically\.?$",
    re.IGNORECASE | re.DOTALL,
)
_CRUSADER_BLOCKER = re.compile(
    r"^Crusader \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"When you deal direct damage with a Blink, Charge, Leap, Teleport, or Pull ability,\s*"
    r"you consecrate the ground beneath you for\s*10 seconds and gain a damage shield that absorbs\s*"
    r"\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*damage for\s*6 seconds\.\s*"
    r"Every\s*2 seconds you and (?:(?:up to\s*11|nearby)\s+)?group members in the area gain "
    r"Minor Courage for\s*12 seconds\.\s*These effects can occur once every\s*20 seconds "
    r"and the damage shield scales off the higher of your Weapon or Spell Damage\.?$",
    re.IGNORECASE | re.DOTALL,
)
_BURNING_SPELLWEAVE_BLOCKER = re.compile(
    r"^Burning Spellweave \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"When you deal damage with a Flame Damage ability,\s*"
    r"you apply the Burning status effect to the enemy and increase your Weapon and Spell Damage by\s*"
    r"(?:\d[\d,]*\s*-\s*)?490\s*for\s*8 seconds\.\s*"
    r"(?:This effect|These effects) can occur once every\s*12 seconds\.?$",
    re.IGNORECASE | re.DOTALL,
)
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
_TRACKERS_LASH_BLOCKER = re.compile(
    r"^Tracker's Lash \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"When your attack is dodged, increase your Weapon and Spell Damage by\s*"
    r"(?:\d[\d,]*\s*-\s*)?95\s*for\s*7 seconds, stacking up to\s*5 times\.\s*"
    r"This effect can occur once every\s*0\.5 seconds\.?$",
    re.IGNORECASE | re.DOTALL,
)
_PELINALS_WRATH_BLOCKER = re.compile(
    r"^Pelinal's Wrath \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Whenever you kill an enemy you gain a damage shield that absorbs up to\s*"
    r"\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*damage for\s*10 seconds and a stack of Wrath of Whitestrake for\s*10 seconds\.\s*"
    r"Each stack of Wrath of Whitestrake grants you\s*(?:\d[\d,]*\s*-\s*)?100\s*Weapon and Spell Damage, but causes you to take\s*"
    r"\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*Oblivion damage every second, up to\s*10 stacks\.\s*"
    r"The damage shield scales off the higher of your Weapon or Spell Damage, and the damage scales off your Max Health\.?$",
    re.IGNORECASE | re.DOTALL,
)

_HEARTLAND_CONQUEROR_BLOCKER = re.compile(
    r"^Heartland Conqueror \(5\): active set bonus is not yet mechanic-mapped:.*Increase the effectiveness of your Weapon Traits by 100%.*$",
    re.IGNORECASE | re.DOTALL,
)
_LIGHT_SPEAKER_BLOCKER = re.compile(
    r"^Light Speaker \(5\): relevant set effect requires condition ability_scope:restoration_staff$",
    re.IGNORECASE,
)
_INNATE_AXIOM_BLOCKER = re.compile(
    r"^Innate Axiom \(5\): relevant set effect requires condition ability_scope:class$",
    re.IGNORECASE,
)
_DAGONS_DOMINION_BLOCKER = re.compile(
    r"^Dagon's Dominion \(5\): relevant set effect requires condition ability_scope:area_of_effect$",
    re.IGNORECASE,
)

_BRIARHEART_BLOCKER = re.compile(
    r"^Briarheart \(5\): active set bonus is not yet mechanic-mapped:.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_MONOLITH_OF_STORMS_BLOCKER = re.compile(
    r"^Monolith of Storms \(5\): active set bonus is not yet mechanic-mapped:.*Each Monolith active grants you\s+\d+(?:-\d+)?\s+Weapon and Spell Damage\.?$",
    re.IGNORECASE | re.DOTALL,
)
_MOON_HUNTER_BLOCKER = re.compile(
    r"^Moon Hunter \(5\): active set bonus is not yet mechanic-mapped:.*alchemical poison.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_MOONDANCER_BLOCKER = re.compile(
    r"^Moondancer \(5\): active set bonus is not yet mechanic-mapped:.*shadow blessing.*Weapon and Spell Damage.*lunar blessing.*Magicka Recovery.*$",
    re.IGNORECASE | re.DOTALL,
)
_RALLYING_CRY_BLOCKER = re.compile(
    r"^Rallying Cry \(5\): active set bonus is not yet mechanic-mapped:.*healing critically strikes.*Battle Spirit.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_SALVATION_BLOCKER = re.compile(
    r"^Salvation \(5\): active set bonus is not yet mechanic-mapped:.*Werewolf form.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_SCATHING_MAGE_BLOCKER = re.compile(
    r"^Scathing Mage \(5\): active set bonus is not yet mechanic-mapped:.*deal direct damage.*chance to increase your Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_SCORIONS_FEAST_BLOCKER = re.compile(
    r"^Scorion's Feast \(5\): active set bonus is not yet mechanic-mapped:.*fully-charged Heavy Attack.*Overflow Aura.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)

_VYKANDS_SOULFURY_BLOCKER = re.compile(
    r"^Vykand's Soulfury \(5\): active set bonus is not yet mechanic-mapped:.*fully-charged Heavy Attack.*Major Force, Major Berserk, or Major Courage.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_YANDIRS_MIGHT_BLOCKER = re.compile(
    r"^Yandir's Might \(5\): active set bonus is not yet mechanic-mapped:.*Critical Damage increases your Weapon and Spell Damage.*fully-charged Heavy Attack removes all stacks.*Weapon and Spell Damage.*$",
    re.IGNORECASE | re.DOTALL,
)
_RED_EAGLES_FURY_BLOCKER = re.compile(
    r"^Red Eagle's Fury \(5\): active set bonus is not yet mechanic-mapped:.*"
    r"Adds\s+(?:\d[\d,]*\s*-\s*)?469\s+Weapon and Spell Damage to your Weapon Skill abilities\.\s*"
    r"Increases the cost of your Weapon Skill abilities by\s*5%\.?$",
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
            "armor master": _ARMOR_MASTER_BLOCKER,
            "basalt-blooded warrior": _BASALT_BLOODED_WARRIOR_BLOCKER,
            "burning spellweave": _BURNING_SPELLWEAVE_BLOCKER,
            "crusader": _CRUSADER_BLOCKER,
            "soulshine": _SOULSHINE_BLOCKER,
            "powerful assault": _POWERFUL_ASSAULT_BLOCKER,
            "voidcaller": _VOIDCALLER_BLOCKER,
            "camonna tong": _CAMONNA_TONG_BLOCKER,
            "ravager": _RAVAGER_BLOCKER,
            "tracker's lash": _TRACKERS_LASH_BLOCKER,
            "pelinal's wrath": _PELINALS_WRATH_BLOCKER,
            "light speaker": _LIGHT_SPEAKER_BLOCKER,
            "innate axiom": _INNATE_AXIOM_BLOCKER,
            "dagon's dominion": _DAGONS_DOMINION_BLOCKER,
            "red eagle's fury": _RED_EAGLES_FURY_BLOCKER,
            "briarheart": _BRIARHEART_BLOCKER,
            "monolith of storms": _MONOLITH_OF_STORMS_BLOCKER,
            "moon hunter": _MOON_HUNTER_BLOCKER,
            "moondancer": _MOONDANCER_BLOCKER,
            "rallying cry": _RALLYING_CRY_BLOCKER,
            "salvation": _SALVATION_BLOCKER,
            "scathing mage": _SCATHING_MAGE_BLOCKER,
            "scorion's feast": _SCORIONS_FEAST_BLOCKER,
            "vykand's soulfury": _VYKANDS_SOULFURY_BLOCKER,
            "yandir's might": _YANDIRS_MIGHT_BLOCKER,
            "heartland conqueror": _HEARTLAND_CONQUEROR_BLOCKER,
        }.get(set_name)
        if set_name == "armor master":
            reviewed_objectives = {"max_health"}
        elif set_name == "basalt-blooded warrior":
            reviewed_objectives = {"healing_done"}
        elif set_name == "heartland conqueror":
            reviewed_objectives = {
                "healing_done",
                "critical_healing",
                "spell_damage",
                "weapon_damage",
            }
        else:
            reviewed_objectives = {"spell_damage", "weapon_damage"}
        if (
            reviewed_blocker is not None
            and objective in reviewed_objectives
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
