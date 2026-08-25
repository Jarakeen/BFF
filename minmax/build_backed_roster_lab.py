from __future__ import annotations

from dataclasses import dataclass, field
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
from .gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from .gear_set_repository import GearSetRepository
from .role import Role


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
    """Disposable Phase 5B bridge from real build ingredients to capabilities.

    This deliberately resolves only sources that the current CharacterBuild
    pipeline can prove. Unknown gear-set bonuses are reported as unsupported,
    never guessed into capabilities.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self.players: list[BuildBackedPlayer] = []

    @staticmethod
    def gear_slots() -> tuple[GearSlot, ...]:
        return tuple(GearSlot)

    def available_gear_sets(self, limit: int = 500) -> tuple[tuple[int, str], ...]:
        if not self.database_path.exists():
            return ()
        import sqlite3

        with sqlite3.connect(self.database_path) as db:
            rows = db.execute(
                "SELECT id, name FROM gear_set ORDER BY name LIMIT ?",
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

        if gear_set_id is not None and gear_pieces > 0:
            repository = GearSetRepository(self.database_path)
            gear_set = repository.get_set_by_id(gear_set_id)
            if gear_set is None:
                validation_errors = (f"Unknown gear set id {gear_set_id}.",)
            else:
                gear_set_name = gear_set.name
                pieces = tuple(
                    ArmorPiece(
                        slot=slot,
                        category=GearPieceCategory.SET_PIECE,
                        set_id=str(gear_set_id),
                    )
                    for slot in GearSlot
                )[: min(gear_pieces, len(tuple(GearSlot)))]
                slots = tuple(
                    SlottedSkill(
                        skill_id=f"test_filler_{index}",
                        skill_line_id="destruction_staff",
                        is_ultimate=(index == 5),
                    )
                    for index in range(6)
                )
                weapon_type = (
                    WeaponType.RESTORATION_STAFF
                    if role == Role.HEALER
                    else WeaponType.SWORD
                )
                bar = Bar(
                    bar_id=active_bar,
                    main_hand=Weapon(weapon_type=weapon_type),
                    off_hand=None,
                    slots=slots,
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
        return player

    def remove_player(self, index: int) -> None:
        del self.players[index]

    def clear(self) -> None:
        self.players.clear()
