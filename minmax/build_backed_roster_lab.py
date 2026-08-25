from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .character_build.bar import Bar
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

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


@dataclass(frozen=True)
class BuildBackedPlayer:
    name: str
    role: Role
    character_class: CharacterClass
    gear_set_id: int | None = None
    gear_set_name: str = ""
    gear_pieces: int = 0
    active_bar: BarId = BarId.FRONT
    resolved_effects: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    unsupported_sources: tuple[str, ...] = ()


class BuildBackedRosterLab:
    """Disposable bridge from real build ingredients to Phase 4 evidence."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self.players: list[BuildBackedPlayer] = []
        self._builds: list[CharacterBuild | None] = []

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

    def add_player(
        self,
        name: str,
        role: Role,
        character_class: CharacterClass,
        gear_set_id: int | None = None,
        gear_pieces: int = 0,
        active_bar: BarId = BarId.FRONT,
    ) -> BuildBackedPlayer:
        gear_set_name = ""
        resolved_effects: tuple[str, ...] = ()
        validation_errors: tuple[str, ...] = ()
        unsupported_sources: tuple[str, ...] = ()
        resolved_build: CharacterBuild | None = None

        if gear_set_id is not None and gear_pieces > 0:
            repository = GearSetRepository(self.database_path)
            gear_set = repository.get_set_by_id(gear_set_id)
            if gear_set is None:
                validation_errors = (f"Unknown gear set id {gear_set_id}.",)
            else:
                gear_set_name = gear_set.name
                slots = tuple(GearSlot)
                pieces = tuple(
                    ArmorPiece(
                        slot=slot,
                        category=GearPieceCategory.SET_PIECE,
                        set_id=str(gear_set_id),
                    )
                    for slot in slots[: min(gear_pieces, len(slots))]
                )
                filler_slots = tuple(
                    SlottedSkill(
                        skill_id=f"test_filler_{index}",
                        skill_line_id="restoration_staff",
                        is_ultimate=(index == 5),
                    )
                    for index in range(6)
                )
                bar = Bar(
                    bar_id=active_bar,
                    main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
                    off_hand=None,
                    slots=filler_slots,
                )
                build = CharacterBuild(
                    name=name.strip() or f"Mock {role.value.title()}",
                    character_class=character_class,
                    role=role,
                    armor=pieces,
                    front_bar=bar if active_bar == BarId.FRONT else None,
                    back_bar=bar if active_bar == BarId.BACK else None,
                )
                validation_errors = build.validate()
                if not validation_errors:
                    resolver = CharacterBuildSupportEffectResolver(
                        gear_set_effect_variant_resolver=GearSetEffectVariantResolver(repository)
                    )
                    registry = resolver.resolve(build, active_bar=active_bar)
                    effects = registry.all()
                    resolved_effects = tuple(effect.name for effect in effects)
                    resolved_build = build
                    if not effects:
                        unsupported_sources = (
                            f"{gear_set_name}: no registered support-effect mapping for the equipped bonus tiers.",
                        )

        player = BuildBackedPlayer(
            name=name.strip() or f"Mock {role.value.title()}",
            role=role,
            character_class=character_class,
            gear_set_id=gear_set_id,
            gear_set_name=gear_set_name,
            gear_pieces=max(0, int(gear_pieces)),
            active_bar=active_bar,
            resolved_effects=resolved_effects,
            validation_errors=validation_errors,
            unsupported_sources=unsupported_sources,
        )
        self.players.append(player)
        self._builds.append(resolved_build)
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
        return RosterCapabilityResolver().resolve(characters, active_bars)

    def evaluate(
        self,
        requirement_set: EncounterRequirementSet | None = None,
        evaluator: EncounterEvaluator | None = None,
    ) -> EncounterEvaluation:
        """Evaluate resolved build evidence through the real Phase 4 engine."""
        requirement_set = requirement_set or MockRosterLab.requirement_set()
        evaluator = evaluator or EncounterEvaluator()
        return evaluator.evaluate(requirement_set, self.capabilities())
