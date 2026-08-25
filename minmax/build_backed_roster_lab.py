from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .character_build.bar import Bar
from .character_build.capability_resolver import CharacterCapabilityResolver
from .character_build.character_build import CharacterBuild
from .character_build.character_class import CharacterClass
from .character_build.effect_layer import BarId
from .character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from .character_build.slotted_skill import SlottedSkill
from .character_build.support_effect_resolver import CharacterBuildSupportEffectResolver
from .character_build.weapon import Weapon
from .character_build.weapon_type import WeaponType
from .encounter_evaluation import EncounterEvaluation, EncounterEvaluator
from .encounter_requirements import EncounterRequirementSet
from .gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from .gear_set_repository import GearSetRepository
from .mock_roster_lab import MockRosterLab
from .role import Role
from .roster_capability_resolver import RosterCapabilityResolver
from .skill_effect_repository import SkillEffectRepository

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


@dataclass(frozen=True)
class BuildBackedPlayer:
    name: str
    role: Role
    character_class: CharacterClass
    gear_set_id: int | None = None
    gear_set_name: str = ""
    gear_pieces: int = 0
    gear_sets: tuple[tuple[int, str, int], ...] = ()
    skills: tuple[tuple[int, str], ...] = ()
    active_bar: BarId = BarId.FRONT
    resolved_effects: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    unsupported_sources: tuple[str, ...] = ()


class BuildBackedRosterLab:
    """Disposable bridge from real build ingredients to Phase 4 evidence."""

    MAX_ARMOR_SLOTS = len(tuple(GearSlot))
    MAX_SKILL_SLOTS = 6

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self.players: list[BuildBackedPlayer] = []
        self._builds: list[CharacterBuild | None] = []
        repository = GearSetRepository(self.database_path)
        self._gear_resolver = GearSetEffectVariantResolver(repository)
        self._skill_repository = SkillEffectRepository(self.database_path)
        self._character_resolver = CharacterCapabilityResolver(
            gear_set_effect_variant_resolver=self._gear_resolver,
        )

    def available_gear_sets(self, limit: int | None = None) -> tuple[tuple[int, str], ...]:
        """Return every gear set in the database unless a caller explicitly limits it."""
        if not self.database_path.exists():
            return ()
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            if limit is None:
                rows = db.execute(
                    "SELECT id, name FROM gear_set ORDER BY name COLLATE NOCASE"
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id, name FROM gear_set ORDER BY name COLLATE NOCASE LIMIT ?",
                    (limit,),
                ).fetchall()
        return tuple((int(row[0]), str(row[1])) for row in rows)

    def available_skills(
        self,
        character_class: CharacterClass | str,
        limit: int | None = 5000,
    ) -> tuple[tuple[int, str], ...]:
        return self._skill_repository.available_skills(character_class, limit)

    def add_player(
        self,
        name: str,
        role: Role,
        character_class: CharacterClass,
        gear_set_id: int | None = None,
        gear_pieces: int = 0,
        active_bar: BarId = BarId.FRONT,
        gear_sets: tuple[tuple[int, int], ...] | None = None,
        skill_ids: tuple[int, ...] = (),
    ) -> BuildBackedPlayer:
        """Add a disposable build-backed player with optional real skill effects."""
        if gear_sets is None:
            gear_sets = (
                ((gear_set_id, gear_pieces),)
                if gear_set_id is not None and gear_pieces > 0
                else ()
            )

        normalized_assignments = tuple(
            (int(set_id), max(0, int(piece_count)))
            for set_id, piece_count in gear_sets
            if int(piece_count) > 0
        )
        normalized_skills = tuple(dict.fromkeys(int(skill_id) for skill_id in skill_ids))

        total_pieces = sum(piece_count for _, piece_count in normalized_assignments)
        validation_errors: list[str] = []
        if total_pieces > self.MAX_ARMOR_SLOTS:
            validation_errors.append(
                f"Mock build has {total_pieces} armor/jewelry set pieces; "
                f"only {self.MAX_ARMOR_SLOTS} slots are available."
            )
        if len(normalized_skills) > self.MAX_SKILL_SLOTS:
            validation_errors.append(
                f"Mock build has {len(normalized_skills)} skills; "
                f"only {self.MAX_SKILL_SLOTS} active-bar slots are available."
            )

        if validation_errors:
            player = BuildBackedPlayer(
                name=name.strip() or f"Mock {role.value.title()}",
                role=role,
                character_class=character_class,
                active_bar=active_bar,
                gear_sets=tuple((set_id, "", pieces) for set_id, pieces in normalized_assignments),
                skills=tuple((skill_id, "") for skill_id in normalized_skills),
                validation_errors=tuple(validation_errors),
            )
            self.players.append(player)
            self._builds.append(None)
            return player

        repository = GearSetRepository(self.database_path)
        resolved_set_metadata: list[tuple[int, str, int]] = []
        resolved_skill_metadata: list[tuple[int, str]] = []
        armor_pieces: list[ArmorPiece] = []
        slot_sequence = tuple(GearSlot)
        slot_index = 0
        unsupported_sources: list[str] = []

        for set_id, piece_count in normalized_assignments:
            gear_set = repository.get_set_by_id(set_id)
            if gear_set is None:
                validation_errors.append(f"Unknown gear set id {set_id}.")
                resolved_set_metadata.append((set_id, f"Unknown set {set_id}", piece_count))
                slot_index += piece_count
                continue

            resolved_set_metadata.append((set_id, gear_set.name, piece_count))
            if not self._gear_resolver.resolve(set_id, piece_count):
                unsupported_sources.append(
                    f"{gear_set.name}: no registered support-effect mapping for the equipped bonus tiers."
                )

            for _ in range(piece_count):
                if slot_index >= len(slot_sequence):
                    break
                armor_pieces.append(
                    ArmorPiece(
                        slot=slot_sequence[slot_index],
                        category=GearPieceCategory.SET_PIECE,
                        set_id=str(set_id),
                    )
                )
                slot_index += 1

        skill_slots: list[SlottedSkill] = []
        for skill_id in normalized_skills:
            rows = self._skill_repository.resolve(skill_id)
            skill_name = ""
            if self.database_path.exists():
                import sqlite3
                with sqlite3.connect(self.database_path) as db:
                    row = db.execute(
                        "SELECT name FROM ability WHERE ability_id = ?",
                        (skill_id,),
                    ).fetchone()
                skill_name = str(row[0]) if row else ""
            resolved_skill_metadata.append((skill_id, skill_name or f"Unknown skill {skill_id}"))
            if not rows:
                unsupported_sources.append(
                    f"{skill_name or f'Ability {skill_id}'}: no linked support-effect mapping."
                )
            skill_slots.append(
                SlottedSkill(
                    skill_id=str(skill_id),
                    skill_line_id="database_ability",
                    is_cast=True,
                    requires_active_bar=True,
                    effects=rows,
                )
            )

        while len(skill_slots) < self.MAX_SKILL_SLOTS:
            index = len(skill_slots)
            skill_slots.append(
                SlottedSkill(
                    skill_id=f"test_filler_{index}",
                    skill_line_id="restoration_staff",
                    is_ultimate=(index == 5),
                )
            )

        bar = Bar(
            bar_id=active_bar,
            main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
            off_hand=None,
            slots=tuple(skill_slots),
        )

        resolved_build = CharacterBuild(
            name=name.strip() or f"Mock {role.value.title()}",
            character_class=character_class,
            role=role,
            armor=tuple(armor_pieces),
            front_bar=bar if active_bar == BarId.FRONT else None,
            back_bar=bar if active_bar == BarId.BACK else None,
        )

        validation_errors.extend(resolved_build.validate())
        resolved_effects: tuple[str, ...] = ()

        if not validation_errors:
            registry = self._character_resolver.resolve(resolved_build, active_bar=active_bar)
            resolved_effects = tuple(effect.name for effect in registry.all())
            if not resolved_effects and (normalized_assignments or normalized_skills) and not unsupported_sources:
                unsupported_sources.append("No support effects were resolved from the selected build ingredients.")

        first_set = resolved_set_metadata[0] if resolved_set_metadata else (None, "", 0)
        player = BuildBackedPlayer(
            name=resolved_build.name,
            role=role,
            character_class=character_class,
            gear_set_id=first_set[0],
            gear_set_name=first_set[1],
            gear_pieces=first_set[2],
            gear_sets=tuple(resolved_set_metadata),
            skills=tuple(resolved_skill_metadata),
            active_bar=active_bar,
            resolved_effects=resolved_effects,
            validation_errors=tuple(validation_errors),
            unsupported_sources=tuple(unsupported_sources),
        )
        self.players.append(player)
        self._builds.append(resolved_build if not validation_errors else None)
        return player

    def remove_player(self, index: int) -> None:
        del self.players[index]
        del self._builds[index]

    def clear(self) -> None:
        self.players.clear()
        self._builds.clear()

    def capabilities(self):
        """Resolve valid mock builds into roster-level capability evidence."""
        characters = [build for build in self._builds if build is not None]
        active_bars = {
            build.name: (BarId.FRONT if build.front_bar is not None else BarId.BACK)
            for build in characters
        }
        return RosterCapabilityResolver(
            character_capability_resolver=self._character_resolver,
        ).resolve(characters, active_bars)

    def evaluate(
        self,
        requirement_set: EncounterRequirementSet | None = None,
        evaluator: EncounterEvaluator | None = None,
    ) -> EncounterEvaluation:
        """Evaluate resolved build evidence through the real Phase 4 engine."""
        requirement_set = requirement_set or MockRosterLab.requirement_set()
        evaluator = evaluator or EncounterEvaluator()
        return evaluator.evaluate(requirement_set, self.capabilities())
