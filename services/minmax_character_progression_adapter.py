from __future__ import annotations

from dataclasses import dataclass

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.character_progression_service import CharacterProgressionService


@dataclass(frozen=True)
class SavedBuildProgressionResolution:
    character_id: str
    progression: CharacterProgression
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.character_id) and not self.unresolved


class MinmaxCharacterProgressionAdapter:
    """Bridge canonical character-owned progression into MinMax inputs."""

    def __init__(self, catalog_service: BuildCatalogService) -> None:
        self.catalog_service = catalog_service
        self.progression_service = CharacterProgressionService(catalog_service)

    @staticmethod
    def _attributes(build: PlayerBuild) -> AttributeAllocation:
        return AttributeAllocation(
            health=int(getattr(build, "AttributeHealth", 0) or 0),
            magicka=int(getattr(build, "AttributeMagicka", 0) or 0),
            stamina=int(getattr(build, "AttributeStamina", 0) or 0),
        )

    def _character_id(self, build: PlayerBuild) -> str | None:
        direct = str(getattr(build, "CharacterId", "") or "").strip()
        if direct and self.catalog_service.get_character(direct) is not None:
            return direct
        return self.progression_service.find_character_id(
            name=str(build.Name or ""),
            gamertag=str(build.Gamertag or ""),
        )

    def resolve(self, build: PlayerBuild) -> SavedBuildProgressionResolution:
        character_id = self._character_id(build)
        if not character_id:
            return SavedBuildProgressionResolution(
                character_id="",
                progression=CharacterProgression(
                    attributes=self._attributes(build),
                    passive_ranks=None,
                    passive_cp_points=None,
                ),
                unresolved=("Canonical character progression could not be resolved for saved build",),
            )

        saved = self.progression_service.get(character_id)
        if saved is None:
            return SavedBuildProgressionResolution(
                character_id=character_id,
                progression=CharacterProgression(
                    attributes=self._attributes(build),
                    passive_ranks=None,
                    passive_cp_points=None,
                ),
                unresolved=(f"Canonical character progression not found: {character_id}",),
            )

        return SavedBuildProgressionResolution(
            character_id=character_id,
            progression=CharacterProgression(
                attributes=self._attributes(build),
                owned_skill_lines=saved.owned_skill_lines,
                passive_ranks=dict(saved.passive_ranks or {}),
                passive_cp_points=dict(saved.passive_cp_points or {}),
            ),
        )
