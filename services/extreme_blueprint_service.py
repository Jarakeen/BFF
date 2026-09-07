from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.gear_set_effect_service import GearSetEffectService
from minmax.passive_math import medium_armor_weapon_spell_damage_percent
from models.build_model import ARMOR_SLOTS, GearSlot, PlayerBuild
from services.extreme_optimization_service import (
    ExtremeObjective,
    ExtremeOptimizationService,
    ExtremeOptimizationStep,
)


_CLASSES = (
    "Arcanist",
    "Dragonknight",
    "Necromancer",
    "Nightblade",
    "Sorcerer",
    "Templar",
    "Warden",
)

# Resting/self-contained Spell Damage proof boundary.
# Expert Mage rank 2: +108 Weapon/Spell Damage for each Sorcerer ability slotted.
# Twin Blade and Blunt rank 2: each equipped sword adds +129 Weapon/Spell Damage.
# These are standing effects. Cast-required Major Sorcery, proc stacks, target state,
# group buffs, potions, and other temporary effects are intentionally excluded.
_SORCERER_EXPERT_MAGE_PER_SLOT = 108.0
_DUAL_WIELD_SWORD_DAMAGE = 129.0
_SORCERER_SPELL_DAMAGE_BAR = (
    "Crystal Fragments",
    "Daedric Prey",
    "Bound Aegis",
    "Summon Volatile Familiar",
    "Mages' Wrath",
    "Power Overload",
)
_MEDIUM_ARMOR_STATIC_PASSIVES = (
    "Wind Walker",
    "Agility",
    "Dexterity",
)


@dataclass(frozen=True)
class ExtremeBlueprintResult:
    objective: ExtremeObjective
    build: PlayerBuild
    value: float
    race: str
    class_label: str
    class_candidates: tuple[str, ...]
    set_package: tuple[str, ...]
    steps: tuple[ExtremeOptimizationStep, ...]
    unresolved: tuple[str, ...]
    notes: tuple[str, ...]


class ExtremeBlueprintService:
    """Build a deliberately absurd stat-maximizing character from an empty shell.

    From-scratch blueprints use a resting/self-contained boundary: equipment,
    food, race, intrinsic passives, and standing effects from skills actually
    slotted on the active bar. Cast-required buffs, group buffs, target debuffs,
    proc windows, potion uptime, and temporary combat states are excluded.
    """

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        builds_path: Path | None = None,
    ) -> None:
        data_dir = get_data_dir()
        self.database_path = Path(database_path or data_dir / "eso.db")
        self.extreme = ExtremeOptimizationService(
            database_path=self.database_path,
            builds_path=builds_path,
        )
        self.set_effects = GearSetEffectService(self.extreme.gear_set_repository)

    def optimize_from_scratch(
        self,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeBlueprintResult:
        objective = self.extreme.objective(objective_key)
        active_bar = "back" if str(active_bar or "front").casefold() == "back" else "front"
        progression = self._resting_progression(objective)

        base = self._blank_build(objective)
        base, class_label, class_candidates = self._apply_resting_profile(
            base,
            objective,
            active_bar=active_bar,
        )
        base = self._best_race(base, objective, progression, active_bar)
        base, set_package = self._best_static_set_package(
            base,
            objective,
            progression,
            active_bar,
        )

        current = base
        current_value, initial_unresolved = self._evaluate_resting(
            current,
            progression=progression,
            character_id="extreme-blueprint",
            build_id="extreme-blueprint:baseline",
            objective=objective,
            active_bar=active_bar,
        )
        unresolved = list(initial_unresolved)
        accepted: list[ExtremeOptimizationStep] = []

        for pass_index in range(max(1, int(max_passes))):
            best = None
            for candidate in self.extreme._candidates(
                current,
                objective=objective,
                character_id="extreme-blueprint",
                baseline_build_id=f"extreme-blueprint:{pass_index}",
            ):
                value, candidate_unresolved = self._evaluate_resting(
                    candidate.candidate_build,
                    progression=progression,
                    character_id="extreme-blueprint",
                    build_id=candidate.candidate_id,
                    objective=objective,
                    active_bar=active_bar,
                )
                unresolved.extend(candidate_unresolved)
                if value <= current_value + 1e-9:
                    continue
                if best is None or value > best[0] + 1e-9 or (
                    abs(value - best[0]) <= 1e-9 and candidate.candidate_id < best[1]
                ):
                    best = (value, candidate.candidate_id, candidate)

            if best is None:
                break

            next_value, _, winner = best
            change = winner.changes[0]
            accepted.append(
                ExtremeOptimizationStep(
                    path=change.path,
                    before=change.before,
                    after=change.after,
                    value_before=current_value,
                    value_after=next_value,
                )
            )
            current = winner.candidate_build
            current_value = next_value

        current.EsoClass = class_label
        current.BuildName = f"Extreme {objective.label} Blueprint"

        notes = (
            "Resting/self-contained boundary: armor, jewelry, weapons, race, Mundus, food, intrinsic passives, and standing effects from skills on the active bar.",
            "Cast-required buffs, group buffs, target debuffs, proc stacks, potion uptime, and temporary combat states are excluded.",
            "Static 5-piece set bonuses are evaluated only when the active-bar equipment actually reaches five pieces.",
            (
                "Spell Damage uses Sorcerer because Expert Mage grants +108 Weapon/Spell Damage per Sorcerer ability slotted. "
                "The active bar is six Sorcerer abilities, armor is Medium for standing Agility, and dual swords receive Twin Blade and Blunt."
                if objective.key == "spell_damage"
                else "Class remains unresolved for this objective until an objective-specific resting class advantage is modeled."
            ),
        )

        return ExtremeBlueprintResult(
            objective=objective,
            build=current,
            value=current_value,
            race=str(current.Race or ""),
            class_label=class_label,
            class_candidates=class_candidates,
            set_package=set_package,
            steps=tuple(accepted),
            unresolved=tuple(dict.fromkeys(x for x in unresolved if x)),
            notes=notes,
        )

    def _resting_progression(self, objective: ExtremeObjective) -> CharacterProgression:
        if objective.key != "spell_damage":
            return CharacterProgression(
                attributes=AttributeAllocation(),
                passive_ranks={},
                passive_cp_points={},
            )

        passive_ranks: dict[str, int] = {}
        repository = self.extreme.context_factory.skill_line_repository
        if repository is not None:
            for passive_name in _MEDIUM_ARMOR_STATIC_PASSIVES:
                maximum = repository.passive_max_rank(passive_name)
                if maximum is not None:
                    passive_ranks[passive_name] = maximum

        return CharacterProgression(
            attributes=AttributeAllocation(),
            owned_skill_lines=("Medium Armor",),
            passive_ranks=passive_ranks,
            passive_cp_points={},
        )

    def _apply_resting_profile(
        self,
        build: PlayerBuild,
        objective: ExtremeObjective,
        *,
        active_bar: str,
    ) -> tuple[PlayerBuild, str, tuple[str, ...]]:
        candidate = PlayerBuild.from_dict(build.to_dict())
        if objective.key != "spell_damage":
            label = "Any class (resting-sheet tie)"
            candidate.EsoClass = label
            return candidate, label, _CLASSES

        candidate.EsoClass = "Sorcerer"
        skills = list(_SORCERER_SPELL_DAMAGE_BAR)
        if active_bar == "back":
            candidate.BackBarSkills = skills
        else:
            candidate.FrontBarSkills = skills

        for entry in candidate.Armor.values():
            entry["Weight"] = "Medium"

        main = GearSlot(
            Set="Blueprint Placeholder",
            Quality="Gold",
            Trait="Nirnhoned",
            Enchant="",
            EnchantTier="Truly Superb",
            Level="CP160",
            WeaponType="Sword",
        )
        off = GearSlot.from_dict(main.to_dict())
        if active_bar == "back":
            candidate.BackBarWeapon = main
            candidate.BackBarOffHand = off
            candidate.FrontBarWeapon = GearSlot.from_dict(main.to_dict())
            candidate.FrontBarOffHand = GearSlot.from_dict(off.to_dict())
        else:
            candidate.FrontBarWeapon = main
            candidate.FrontBarOffHand = off
            candidate.BackBarWeapon = GearSlot.from_dict(main.to_dict())
            candidate.BackBarOffHand = GearSlot.from_dict(off.to_dict())
        return candidate, "Sorcerer", ("Sorcerer",)

    def _evaluate_resting(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        objective: ExtremeObjective,
        active_bar: str,
    ) -> tuple[float, tuple[str, ...]]:
        value, unresolved = self.extreme._evaluate(
            build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            objective=objective,
            active_bar=active_bar,
        )
        if objective.key == "spell_damage":
            value += self._resting_spell_damage_bonus(build, active_bar=active_bar)
        return value, unresolved

    @staticmethod
    def _resting_spell_damage_bonus(build: PlayerBuild, *, active_bar: str) -> float:
        if str(build.EsoClass or "").strip().casefold() != "sorcerer":
            return 0.0
        skills = build.BackBarSkills if active_bar == "back" else build.FrontBarSkills
        slotted = sum(1 for skill in skills[:6] if str(skill or "").strip())
        flat_bonus = _SORCERER_EXPERT_MAGE_PER_SLOT * slotted

        main, offhand = build.active_weapon_slots(active_bar)
        for slot in (main, offhand):
            if str(slot.WeaponType or "").strip().casefold() == "sword":
                flat_bonus += _DUAL_WIELD_SWORD_DAMAGE

        medium_count = sum(
            1
            for entry in build.Armor.values()
            if str(entry.get("Weight", "") or "").strip().casefold() == "medium"
        )
        agility_percent = medium_armor_weapon_spell_damage_percent(medium_count)
        return flat_bonus * (1.0 + agility_percent)

    def _blank_build(self, objective: ExtremeObjective) -> PlayerBuild:
        build = PlayerBuild(
            Name="Jane / John Doe",
            BuildName=f"Extreme {objective.label} Blueprint",
            Race="",
            EsoClass="",
            Role="Experimental",
        )
        if objective.key == "max_health":
            build.AttributeHealth = 64
        elif objective.key == "max_magicka":
            build.AttributeMagicka = 64
        elif objective.key == "max_stamina":
            build.AttributeStamina = 64

        for slot_name in ARMOR_SLOTS:
            build.Armor[slot_name].update(
                {
                    "Set": "Blueprint Placeholder",
                    "Quality": "Gold",
                    "Trait": "Divines",
                    "Enchant": "Max Magicka",
                    "EnchantTier": "Truly Superb",
                    "Level": "CP160",
                    "Weight": "Light",
                }
            )

        for field_name in ("Necklace", "Ring1", "Ring2"):
            setattr(
                build,
                field_name,
                GearSlot(
                    Set="Blueprint Placeholder",
                    Quality="Gold",
                    Trait="Infused",
                    Enchant="Spell Damage",
                    EnchantTier="Truly Superb",
                    Level="CP160",
                ),
            )

        build.FrontBarWeapon = GearSlot(
            Set="Blueprint Placeholder",
            Quality="Gold",
            Trait="Nirnhoned",
            Enchant="",
            EnchantTier="Truly Superb",
            Level="CP160",
            WeaponType="Inferno Staff",
        )
        build.BackBarWeapon = GearSlot.from_dict(build.FrontBarWeapon.to_dict())
        return build

    def _race_names(self) -> tuple[str, ...]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute("SELECT name FROM race ORDER BY name").fetchall()
        return tuple(str(row[0]) for row in rows if str(row[0] or "").strip())

    def _best_race(
        self,
        build: PlayerBuild,
        objective: ExtremeObjective,
        progression: CharacterProgression,
        active_bar: str,
    ) -> PlayerBuild:
        best_build = PlayerBuild.from_dict(build.to_dict())
        best_value = float("-inf")
        for race in self._race_names():
            candidate = PlayerBuild.from_dict(build.to_dict())
            candidate.Race = race
            value, _ = self._evaluate_resting(
                candidate,
                progression=progression,
                character_id="extreme-blueprint",
                build_id=f"extreme-blueprint:race:{race}",
                objective=objective,
                active_bar=active_bar,
            )
            if value > best_value + 1e-9 or (
                abs(value - best_value) <= 1e-9 and race < str(best_build.Race or "~")
            ):
                best_value = value
                best_build = candidate
        return best_build

    def _five_piece_set_names(self) -> tuple[str, ...]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM gear_set
                WHERE COALESCE(max_equip_count, 0) >= 5
                ORDER BY name
                """
            ).fetchall()
        return tuple(str(row[0]) for row in rows if str(row[0] or "").strip())

    def _set_static_score(self, name: str, objective: ExtremeObjective) -> float:
        gear_set = self.extreme.gear_set_repository.get_set(name)
        if gear_set is None:
            return 0.0
        effects = self.set_effects.resolve_effects(gear_set.id, 5)
        stat = None
        if objective.key in {
            "max_health", "max_magicka", "max_stamina",
            "health_recovery", "magicka_recovery", "stamina_recovery",
        }:
            from minmax.stat_ids import StatId
            stat = {
                "max_health": StatId.MAX_HEALTH,
                "max_magicka": StatId.MAX_MAGICKA,
                "max_stamina": StatId.MAX_STAMINA,
                "health_recovery": StatId.HEALTH_RECOVERY,
                "magicka_recovery": StatId.MAGICKA_RECOVERY,
                "stamina_recovery": StatId.STAMINA_RECOVERY,
            }[objective.key]
        else:
            from services.extreme_optimization_service import _STAT_ID_BY_OBJECTIVE
            stat = _STAT_ID_BY_OBJECTIVE.get(objective.key)
        if stat is None:
            return 0.0
        return sum(float(effect.value) for effect in effects if effect.stat == stat)

    def _best_static_set_package(
        self,
        build: PlayerBuild,
        objective: ExtremeObjective,
        progression: CharacterProgression,
        active_bar: str,
    ) -> tuple[PlayerBuild, tuple[str, ...]]:
        ranked = sorted(
            (
                (self._set_static_score(name, objective), name)
                for name in self._five_piece_set_names()
            ),
            key=lambda row: (-row[0], row[1]),
        )
        names = [name for score, name in ranked if score > 0][:18]
        if not names:
            return build, ()

        best_build = PlayerBuild.from_dict(build.to_dict())
        best_value = float("-inf")
        best_pair: tuple[str, ...] = ()
        for first in names:
            for second in names:
                if second == first:
                    continue
                candidate = PlayerBuild.from_dict(build.to_dict())
                for slot_name in ("Chest", "Hands", "Waist", "Legs", "Feet"):
                    candidate.Armor[slot_name]["Set"] = first
                for field_name in ("Necklace", "Ring1", "Ring2"):
                    getattr(candidate, field_name).Set = second

                if active_bar == "back":
                    candidate.BackBarWeapon.Set = second
                    candidate.BackBarOffHand.Set = second
                else:
                    candidate.FrontBarWeapon.Set = second
                    candidate.FrontBarOffHand.Set = second

                candidate.Armor["Head"]["Set"] = ""
                candidate.Armor["Shoulders"]["Set"] = ""
                value, _ = self._evaluate_resting(
                    candidate,
                    progression=progression,
                    character_id="extreme-blueprint",
                    build_id=f"extreme-blueprint:sets:{first}:{second}",
                    objective=objective,
                    active_bar=active_bar,
                )
                if value > best_value + 1e-9 or (
                    abs(value - best_value) <= 1e-9 and (first, second) < best_pair
                ):
                    best_value = value
                    best_build = candidate
                    best_pair = (first, second)
        return best_build, best_pair
