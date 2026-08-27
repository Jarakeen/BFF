from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from models.build_model import PlayerBuild
from services.skill_choice_service import load_skill_choices
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.skill_coefficient import SkillCoefficientResult, evaluate_skill_coefficient
from minmax.skill_coefficient_service import SkillCoefficientService
from minmax.skill_effect_repository import SkillEffectRepository
from services.eso_database import EsoDatabase


@dataclass(frozen=True)
class ResolvedSkill:
    name: str
    ability_id: int
    skill_rank_id: int
    morph: int
    effects: tuple
    coefficients: tuple


@dataclass(frozen=True)
class ResolvedGearSet:
    name: str
    set_id: int
    piece_count: int
    effects: tuple


@dataclass(frozen=True)
class BuildMathSnapshot:
    """Database-backed mechanical evidence for one saved PlayerBuild.

    This is the bridge between the UI's persisted build shape and the
    calculation/effect layers. It deliberately does not invent final stats:
    max-stat/power/penetration/crit inputs belong to the stat model and are
    supplied when a numerical skill calculation is requested.
    """

    player_name: str
    build_name: str
    class_name: str
    role: str
    vampire: bool
    werewolf: bool
    gear_sets: tuple[ResolvedGearSet, ...]
    skills: tuple[ResolvedSkill, ...]
    unresolved_skills: tuple[str, ...]
    unresolved_gear_sets: tuple[str, ...]

    @property
    def effects(self) -> tuple:
        effects = []
        for gear_set in self.gear_sets:
            effects.extend(gear_set.effects)
        for skill in self.skills:
            effects.extend(skill.effects)
        return tuple(effects)


class BuildMathService:
    """Resolve saved Builds-page data into the canonical Phase 5 engine.

    No effect identity is inferred from display text. Skills are resolved
    through the canonical skill/morph choices and gear through gear_set.
    Numeric skill math uses the existing coefficient service, preserving the
    imported ESO A/B/C/R values already stored in eso.db.
    """

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database = EsoDatabase(self.database_path)
        self.skill_choices = load_skill_choices(self.database_path)
        self._skill_by_name = {
            str(record.get("name") or "").strip().casefold(): record
            for record in self.skill_choices
            if str(record.get("name") or "").strip()
        }
        self.gear_repository = GearSetRepository(self.database_path)
        self.gear_resolver = GearSetEffectVariantResolver(self.gear_repository)
        self.skill_effects = SkillEffectRepository(self.database_path)
        self.coefficients = SkillCoefficientService(self.database)

    def resolve_build(self, build: PlayerBuild) -> BuildMathSnapshot:
        gear_counts = self._gear_set_counts(build)
        gear_sets: list[ResolvedGearSet] = []
        unresolved_gear: list[str] = []

        for name, count in sorted(gear_counts.items(), key=lambda item: item[0].casefold()):
            gear_set = self._find_gear_set(name)
            if gear_set is None:
                unresolved_gear.append(name)
                continue
            effects = tuple(self.gear_resolver.resolve(gear_set.id, count))
            gear_sets.append(
                ResolvedGearSet(
                    name=gear_set.name,
                    set_id=int(gear_set.id),
                    piece_count=count,
                    effects=effects,
                )
            )

        skills: list[ResolvedSkill] = []
        unresolved_skills: list[str] = []
        seen_ability_ids: set[int] = set()

        for skill_name in self._selected_skill_names(build):
            record = self._skill_by_name.get(skill_name.casefold())
            if record is None:
                unresolved_skills.append(skill_name)
                continue

            ability_id = int(record["ability_id"])
            if ability_id in seen_ability_ids:
                continue
            seen_ability_ids.add(ability_id)

            rank_id = self._skill_rank_id(ability_id)
            if rank_id is None:
                unresolved_skills.append(skill_name)
                continue

            try:
                effects = self.skill_effects.resolve(ability_id)
            except sqlite3.Error:
                effects = ()

            coefficients = self.coefficients.get_for_skill_rank(rank_id)
            skills.append(
                ResolvedSkill(
                    name=str(record["name"]),
                    ability_id=ability_id,
                    skill_rank_id=rank_id,
                    morph=int(record.get("morph") or 0),
                    effects=effects,
                    coefficients=coefficients,
                )
            )

        return BuildMathSnapshot(
            player_name=build.Name.strip() or build.Gamertag.strip(),
            build_name=build.BuildName.strip(),
            class_name=build.EsoClass.strip(),
            role=build.Role.strip(),
            vampire=bool(build.Vampire),
            werewolf=bool(build.Werewolf),
            gear_sets=tuple(gear_sets),
            skills=tuple(skills),
            unresolved_skills=tuple(unresolved_skills),
            unresolved_gear_sets=tuple(unresolved_gear),
        )

    def evaluate_skill(
        self,
        snapshot: BuildMathSnapshot,
        skill_name: str,
        *,
        max_stat: float,
        power: float,
    ) -> tuple[SkillCoefficientResult, ...]:
        """Evaluate all imported type-8 coefficient components for a skill."""
        wanted = skill_name.strip().casefold()
        for skill in snapshot.skills:
            if skill.name.strip().casefold() != wanted:
                continue
            results: list[SkillCoefficientResult] = []
            for coefficient in skill.coefficients:
                if coefficient.type != "8" or coefficient.a < 0:
                    continue
                results.append(
                    evaluate_skill_coefficient(
                        coefficient,
                        max_stat=max_stat,
                        power=power,
                    )
                )
            return tuple(results)
        return ()

    def evaluate_build_skills(
        self,
        snapshot: BuildMathSnapshot,
        *,
        max_stat: float,
        power: float,
    ) -> dict[str, tuple[SkillCoefficientResult, ...]]:
        """Evaluate every selected skill using the database's coefficients."""
        return {
            skill.name: self.evaluate_skill(
                snapshot,
                skill.name,
                max_stat=max_stat,
                power=power,
            )
            for skill in snapshot.skills
        }

    @staticmethod
    def _selected_skill_names(build: PlayerBuild) -> tuple[str, ...]:
        return tuple(
            skill.strip()
            for skill in list(build.FrontBarSkills) + list(build.BackBarSkills)
            if skill and skill.strip()
        )

    @staticmethod
    def _gear_set_counts(build: PlayerBuild) -> dict[str, int]:
        counts: Counter[str] = Counter()

        def add(value: str) -> None:
            name = str(value or "").strip()
            if name:
                counts[name] += 1

        for entry in build.Armor.values():
            if isinstance(entry, dict):
                add(entry.get("Set", ""))
                add(entry.get("Set2", ""))

        for entry in (
            build.FrontBarWeapon,
            build.BackBarWeapon,
            build.Necklace,
            build.Ring1,
            build.Ring2,
        ):
            add(entry.Set)
            add(entry.Set2)

        return dict(counts)

    def _find_gear_set(self, name: str):
        exact = self.gear_repository.get_set(name)
        if exact is not None:
            return exact

        with sqlite3.connect(self.database_path) as db:
            row = db.execute(
                "SELECT id, name, category, max_equip_count FROM gear_set WHERE name COLLATE NOCASE = ? LIMIT 1",
                (name,),
            ).fetchone()
        if row is None:
            return None
        from minmax.gear_sets import GearSet
        return GearSet(id=row[0], name=row[1], category=row[2], max_equip_count=row[3])

    def _skill_rank_id(self, ability_id: int) -> int | None:
        with sqlite3.connect(self.database_path) as db:
            row = db.execute(
                "SELECT id FROM skill_rank WHERE ability_id = ? ORDER BY id LIMIT 1",
                (ability_id,),
            ).fetchone()
        return int(row[0]) if row is not None else None
