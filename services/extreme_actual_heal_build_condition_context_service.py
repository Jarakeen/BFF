from __future__ import annotations

"""Compose proven condition markers for standing Extreme H1 scoring.

This service owns no stat arithmetic. It materializes conditions proven directly
by the saved/hypothetical build and the standing H1 scenario, then composes
specialist pre-event witnesses for reviewed runtime setup mechanics. Pet, dodge,
proc, stack, and other runtime conditions remain absent until a specialist service
proves them.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    BURNING_SPELLWEAVE_POWER_CONDITION,
    POWERFUL_ASSAULT_POWER_CONDITION,
    RAVAGER_FULL_STACKS_CONDITION,
    SEVENTH_LEGION_BRUTE_POWER_CONDITION,
    SOULSHINE_POWER_CONDITION,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION,
    CRUSADER_MINOR_COURAGE_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    DEALS_DIRECT_MOBILITY_DAMAGE,
    DEALS_FLAME_DAMAGE,
    GRANTS_RESOLVE,
    HAS_CAST_OR_CHANNEL_TIME,
    IS_ARMOR_ABILITY,
    IS_ASSAULT_ABILITY,
    IS_EARTHEN_HEART_ABILITY,
    REDUCES_TARGET_RESISTANCE,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext


_DESTRUCTION_STAFF_TYPES = frozenset(
    {"inferno staff", "lightning staff", "ice staff", "destruction staff"}
)
_REVIEWED_SETUP_CONDITIONS = (
    ("Armor Master", IS_ARMOR_ABILITY, "armor_ability_slotted", "persistent slotted", None, "active"),
    ("Basalt-Blooded Warrior", IS_EARTHEN_HEART_ABILITY, BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION, "10-second Obsidian Stance", "back", "inactive"),
    ("Burning Spellweave", DEALS_FLAME_DAMAGE, BURNING_SPELLWEAVE_POWER_CONDITION, "8-second", None, "inactive"),
    ("Crusader", DEALS_DIRECT_MOBILITY_DAMAGE, CRUSADER_MINOR_COURAGE_CONDITION, "12-second Minor Courage", None, "inactive"),
    ("Seventh Legion Brute", GRANTS_RESOLVE, SEVENTH_LEGION_BRUTE_POWER_CONDITION, "15-second", None, "inactive"),
    ("Soulshine", HAS_CAST_OR_CHANNEL_TIME, SOULSHINE_POWER_CONDITION, "5-second", None, "inactive"),
    ("Powerful Assault", IS_ASSAULT_ABILITY, POWERFUL_ASSAULT_POWER_CONDITION, "15-second", None, "inactive"),
    ("Ravager", REDUCES_TARGET_RESISTANCE, RAVAGER_FULL_STACKS_CONDITION, "10-second full-stack", None, "inactive"),
)


@dataclass(frozen=True)
class ExtremeActualHealBuildConditionContext:
    active_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def condition_context(self) -> frozenset[str]:
        return frozenset(self.active_conditions)


class ExtremeActualHealBuildConditionContextService:
    """Resolve build/scenario conditions plus reviewed pre-H1 setup witnesses."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        gear_preconditions: ExtremeActualHealGearPreconditionWitnessService | None = None,
        setup_action_legality: ExtremeActualHealSetupActionLegalityService | None = None,
    ) -> None:
        self.database_path = str(database_path)
        self.gear_preconditions = gear_preconditions or ExtremeActualHealGearPreconditionWitnessService()
        self.setup_action_legality = setup_action_legality or ExtremeActualHealSetupActionLegalityService(database_path)
        self._provisioning_kind_cache: dict[str, str | None] = {}

    def _provisioning_kind(self, name: str) -> str | None:
        selected = str(name or "").strip()
        if not selected:
            return None
        key = selected.casefold()
        if key in self._provisioning_kind_cache:
            return self._provisioning_kind_cache[key]
        kind: str | None = None
        with sqlite3.connect(self.database_path) as connection:
            table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='entity'").fetchone()
            if table is not None:
                row = connection.execute(
                    """SELECT entity_type FROM entity WHERE lower(name)=lower(?) AND entity_type IN ('food', 'drink', 'provisioning') ORDER BY CASE entity_type WHEN 'food' THEN 0 WHEN 'drink' THEN 1 ELSE 2 END LIMIT 1""",
                    (selected,),
                ).fetchone()
                if row is not None:
                    candidate = str(row[0] or "").strip().casefold()
                    if candidate in {"food", "drink"}:
                        kind = candidate
        self._provisioning_kind_cache[key] = kind
        return kind

    @staticmethod
    def _bar_skills(
        build: PlayerBuild,
        active_bar: str,
        *,
        placement: str,
    ) -> tuple[str, ...]:
        bar = str(active_bar or "front").strip().casefold()
        want_active = str(placement or "inactive").strip().casefold() == "active"
        values = build.BackBarSkills if (bar == "back") is want_active else build.FrontBarSkills
        return tuple(str(value or "").strip() for value in list(values)[:5])

    @staticmethod
    def _armor_lines(build: PlayerBuild) -> tuple[str, ...]:
        names = {
            f"{str(entry.get('Weight', '') or '').strip()} Armor"
            for entry in build.Armor.values()
            if str(entry.get("Weight", "") or "").strip().casefold()
            in {"light", "medium", "heavy"}
        }
        return tuple(sorted(names, key=str.casefold))

    @classmethod
    def _legality_context(cls, build: PlayerBuild) -> ExtremePlayerSkillLegalityContext:
        return ExtremePlayerSkillLegalityContext(
            equipped_class_lines=tuple(build.ClassSkillLines or ()),
            equipped_armor_lines=cls._armor_lines(build),
            vampire=bool(build.Vampire),
            werewolf=bool(build.Werewolf),
            transformed_form=str(build.TransformedForm or "").strip() or None,
        )

    def _setup_condition_active(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        set_name: str,
        capability: str,
        required_active_bar: str | None = None,
        placement: str = "inactive",
    ) -> tuple[bool, str | None]:
        normalized_bar = str(active_bar or "front").strip().casefold()
        if required_active_bar is not None and normalized_bar != required_active_bar:
            return False, None
        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=normalized_bar)
        if int(counts.get(set_name, 0)) < 5:
            return False, None
        witness = self.setup_action_legality.witness(capability, self._legality_context(build))
        if not witness.proven or not str(witness.skill_name or "").strip():
            return False, None
        wanted = str(witness.skill_name).strip().casefold()
        if not any(
            skill.casefold() == wanted
            for skill in self._bar_skills(build, active_bar, placement=placement)
        ):
            return False, witness.skill_name
        return True, witness.skill_name

    def resolve(self, build: PlayerBuild, *, active_bar: str = "front") -> ExtremeActualHealBuildConditionContext:
        active: set[str] = {"standing_still"}
        evidence: list[str] = ["standing_still: standing H1 scenario definition"]
        unresolved: list[str] = []

        food = str(build.Food or "").strip()
        if food:
            kind = self._provisioning_kind(food)
            if kind == "food":
                active.add("food_buff_active")
                evidence.append(f"food_buff_active: canonical provisioning type for {food}")
            elif kind == "drink":
                active.add("drink_buff_active")
                evidence.append(f"drink_buff_active: canonical provisioning type for {food}")
            else:
                unresolved.append(f"Selected provisioning item has no canonical food/drink type: {food}")

        main, _ = build.active_weapon_slots(active_bar)
        weapon_type = str(main.WeaponType or "").strip().casefold()
        if weapon_type in _DESTRUCTION_STAFF_TYPES:
            active.add("destruction_staff_equipped")
            evidence.append(f"destruction_staff_equipped: active weapon type is {weapon_type}")

        transformed = str(build.TransformedForm or "").strip().casefold()
        if transformed:
            active.add("transformed")
            evidence.append(f"transformed: explicit build form is {transformed}")

        for (
            set_name,
            capability,
            condition,
            window,
            required_active_bar,
            placement,
        ) in _REVIEWED_SETUP_CONDITIONS:
            is_active, skill_name = self._setup_condition_active(
                build,
                active_bar=active_bar,
                set_name=set_name,
                capability=capability,
                required_active_bar=required_active_bar,
                placement=placement,
            )
            if is_active:
                active.add(condition)
                if set_name == "Armor Master":
                    evidence.append(
                        f"{condition}: scored active-bar {skill_name} is a canonical Armor "
                        "ability compatible with an equipped armor weight; Armor Master's "
                        "5% Max Health condition remains active while it stays slotted"
                    )
                elif set_name == "Basalt-Blooded Warrior":
                    evidence.append(
                        f"{condition}: primary/front-bar {skill_name} is a route-legal Earthen Heart "
                        "setup action; cast it for Rock Stance, swap to the secondary/back bar, and "
                        "score inside the 10-second Obsidian Stance window"
                    )
                elif set_name == "Ravager":
                    evidence.append(
                        f"{condition}: inactive-bar {skill_name} is a route-legal resistance-reduction setup action; "
                        "perform four qualifying attempts no faster than one per second, swap back, and score "
                        "inside Ravager's doubled 10-second full-stack window"
                    )
                else:
                    evidence.append(
                        f"{condition}: inactive-bar {skill_name} is a route-legal {capability} setup action; "
                        f"activate it, swap back, and score within {set_name}'s {window} power window"
                    )

        preconditions = self.gear_preconditions.resolve(build, active_bar=active_bar)
        active.update(preconditions.active_conditions)
        evidence.extend(preconditions.evidence)
        unresolved.extend(preconditions.unresolved)

        return ExtremeActualHealBuildConditionContext(
            active_conditions=tuple(sorted(active, key=str.casefold)),
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeActualHealBuildConditionContext",
    "ExtremeActualHealBuildConditionContextService",
]
