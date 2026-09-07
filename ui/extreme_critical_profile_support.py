from __future__ import annotations

"""Correct the from-scratch Spell Critical profile without widening core combat math."""

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import GearSlot, PlayerBuild

_INSTALLED = False

_PRESSURE_POINTS_RATING_PER_NIGHTBLADE_SLOT = 438.0
_DAGGER_CRIT_RATING = 657.0
_MAJOR_CRIT_RATING = 2629.0

_NIGHTBLADE_CRIT_BAR = (
    "Killer's Blade",
    "Relentless Focus",
    "Concealed Weapon",
    "Twisting Path",
    "Healthy Offering",
    "Incapacitating Strike",
)

_MAJOR_CRIT_SKILLS = frozenset(
    {
        "relentless focus",
        "merciless resolve",
        "inner light",
        "radiant magelight",
        "magelight",
    }
)


def _active_skills(build: PlayerBuild, active_bar: str) -> list[str]:
    values = build.BackBarSkills if str(active_bar or "front").casefold() == "back" else build.FrontBarSkills
    return [str(value or "").strip() for value in values[:6] if str(value or "").strip()]


def critical_profile_rating(build: PlayerBuild, *, active_bar: str) -> float:
    """Return standing crit rating omitted from the generic static resolver.

    This patch is intentionally narrow: Nightblade Pressure Points, a slotted
    Major Prophecy/Savagery source, and Twin Blade and Blunt's dagger bonus.
    """
    rating = 0.0
    skills = _active_skills(build, active_bar)

    if str(build.EsoClass or "").strip().casefold() == "nightblade":
        known = {name.casefold() for name in _NIGHTBLADE_CRIT_BAR}
        nightblade_slots = sum(1 for skill in skills if skill.casefold() in known)
        rating += _PRESSURE_POINTS_RATING_PER_NIGHTBLADE_SLOT * nightblade_slots

    if any(skill.casefold() in _MAJOR_CRIT_SKILLS for skill in skills):
        rating += _MAJOR_CRIT_RATING

    main, offhand = build.active_weapon_slots(active_bar)
    for slot in (main, offhand):
        if str(slot.WeaponType or "").strip().casefold() == "dagger":
            rating += _DAGGER_CRIT_RATING

    return rating


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services.extreme_blueprint_service import ExtremeBlueprintService

    original_progression = ExtremeBlueprintService._resting_progression
    original_profile = ExtremeBlueprintService._apply_resting_profile
    original_evaluate = ExtremeBlueprintService._evaluate_snapshot
    original_optimize = ExtremeBlueprintService.optimize_from_scratch

    def progression_with_spell_crit(self, objective):
        if objective.key != "spell_critical":
            return original_progression(self, objective)

        passive_ranks: dict[str, int] = {}
        repository = self.extreme.context_factory.skill_line_repository
        if repository is not None:
            maximum = repository.passive_max_rank("Prodigy")
            if maximum is not None:
                passive_ranks["Prodigy"] = maximum

        return CharacterProgression(
            attributes=AttributeAllocation(),
            owned_skill_lines=("Light Armor",),
            passive_ranks=passive_ranks,
            passive_cp_points={},
        )

    def profile_with_spell_crit(self, build, objective, *, active_bar):
        if objective.key != "spell_critical":
            return original_profile(self, build, objective, active_bar=active_bar)

        candidate = PlayerBuild.from_dict(build.to_dict())
        candidate.EsoClass = "Nightblade"
        candidate.FrontBarSkills = list(_NIGHTBLADE_CRIT_BAR)
        candidate.BackBarSkills = list(_NIGHTBLADE_CRIT_BAR)

        for entry in candidate.Armor.values():
            entry["Weight"] = "Light"

        dagger = GearSlot(
            Set="Blueprint Placeholder",
            Quality="Gold",
            Trait="Precise",
            Enchant="",
            EnchantTier="Truly Superb",
            Level="CP160",
            WeaponType="Dagger",
        )
        candidate.FrontBarWeapon = GearSlot.from_dict(dagger.to_dict())
        candidate.FrontBarOffHand = GearSlot.from_dict(dagger.to_dict())
        candidate.BackBarWeapon = GearSlot.from_dict(dagger.to_dict())
        candidate.BackBarOffHand = GearSlot.from_dict(dagger.to_dict())
        return candidate, "Nightblade", ("Nightblade",)

    def evaluate_with_spell_crit(
        self,
        build,
        *,
        progression,
        character_id,
        build_id,
        objective,
        active_bar,
        potion_buff="",
    ):
        if objective.key != "spell_critical":
            return original_evaluate(
                self,
                build,
                progression=progression,
                character_id=character_id,
                build_id=build_id,
                objective=objective,
                active_bar=active_bar,
                potion_buff=potion_buff,
            )

        skills = _active_skills(build, active_bar)
        has_major_crit = any(skill.casefold() in _MAJOR_CRIT_SKILLS for skill in skills)
        applied_potion = "" if has_major_crit and potion_buff in {"Major Prophecy", "Major Savagery"} else potion_buff

        value, unresolved = original_evaluate(
            self,
            build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            objective=objective,
            active_bar=active_bar,
            potion_buff=applied_potion,
        )
        rating = critical_profile_rating(build, active_bar=active_bar)
        value += GearStatInputResolver.critical_rating_to_ratio(rating)
        return value, unresolved

    def optimize_with_spell_crit(self, objective_key, *, active_bar="front", max_passes=24):
        result = original_optimize(self, objective_key, active_bar=active_bar, max_passes=max_passes)
        if result.objective.key != "spell_critical":
            return result

        notes = tuple(
            note
            for note in result.notes
            if not note.startswith("No proven class-specific standing winner is modeled for this objective")
        ) + (
            "Spell Critical resolves to Nightblade: Pressure Points rewards each Nightblade ability slotted, Relentless Focus supplies the standing Major critical buff, Light Armor contributes Prodigy, and dual daggers contribute Twin Blade and Blunt critical rating.",
            "Race does not currently have a proven raw Critical Chance winner in the modeled racial package; the displayed race is one representative from the tied top group rather than a claimed crit racial.",
            "A crit potion does not stack with the same Major critical buff already supplied by the slotted skill, so potion-active may legitimately equal the resting result.",
        )
        race_label = str(result.race or "").strip()
        if race_label and "representative" not in race_label.casefold():
            race_label = f"{race_label} (representative racial tie)"
        return replace(result, race=race_label, notes=notes)

    ExtremeBlueprintService._resting_progression = progression_with_spell_crit
    ExtremeBlueprintService._apply_resting_profile = profile_with_spell_crit
    ExtremeBlueprintService._evaluate_snapshot = evaluate_with_spell_crit
    ExtremeBlueprintService.optimize_from_scratch = optimize_with_spell_crit
    _INSTALLED = True
