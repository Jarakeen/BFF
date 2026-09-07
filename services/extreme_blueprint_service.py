from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.gear_set_effect_service import GearSetEffectService
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

    This service uses the same canonical static character-sheet calculation stack
    as ExtremeOptimizationService. It is intentionally conservative about what
    it calls proven: class-specific passive/proc advantages are not invented when
    the static stack cannot distinguish them.
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
        progression = CharacterProgression(
            attributes=AttributeAllocation(),
            passive_ranks={},
            passive_cp_points={},
        )

        base = self._blank_build(objective)
        base = self._best_race(base, objective, progression, active_bar)
        base, set_package = self._best_static_set_package(
            base,
            objective,
            progression,
            active_bar,
        )

        current = base
        current_value, initial_unresolved = self.extreme._evaluate(
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
                value, candidate_unresolved = self.extreme._evaluate(
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

        # The current static context does not apply a generic, fully-maxed
        # class-passive package for every class. Do not manufacture a winner.
        class_label = "Any class (static-sheet tie)"
        current.EsoClass = class_label
        current.BuildName = f"Extreme {objective.label} Blueprint"

        notes = (
            "Starts from a fully equipped CP160 template rather than a saved character.",
            "Race, static gear-set bonuses, Mundus, traits, enchants, attributes, and food are searched with BFF's canonical static math.",
            "Class is shown as a tie until BFF can prove comparable fully-maxed class-passive packages for every class.",
            "Runtime proc stacks, target-only conditions, group-only buffs, and temporary combat states are not treated as permanently active.",
        )

        return ExtremeBlueprintResult(
            objective=objective,
            build=current,
            value=current_value,
            race=str(current.Race or ""),
            class_label=class_label,
            class_candidates=_CLASSES,
            set_package=set_package,
            steps=tuple(accepted),
            unresolved=tuple(dict.fromkeys(x for x in unresolved if x)),
            notes=notes,
        )

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
            value, _ = self.extreme._evaluate(
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

        # Evaluate legal-ish 5/5 front-bar packages through the real context,
        # rather than assuming isolated tooltip bonuses add linearly.
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
                candidate.FrontBarWeapon.Set = second
                candidate.BackBarWeapon.Set = second
                # Keep head/shoulder open rather than inventing a 2-piece winner
                # without proven item-slot legality.
                candidate.Armor["Head"]["Set"] = ""
                candidate.Armor["Shoulders"]["Set"] = ""
                value, _ = self.extreme._evaluate(
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
