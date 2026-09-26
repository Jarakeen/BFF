from __future__ import annotations

"""Strict Pydantic boundary for the canonical user-owned Build catalog."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


def _clean(value: object) -> str:
    return str(value or "").strip()


class _CatalogRecord(BaseModel):
    # Build payloads intentionally retain the large compatibility snapshot while
    # canonical identity/reference fields are validated here.
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)


class PlayerCatalogPayload(_CatalogRecord):
    player_id: str = Field(min_length=1, max_length=200)
    gamertag: str = Field(default="", max_length=200)
    display_name: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=8000)
    status: str = Field(default="Active", min_length=1, max_length=80)
    avatar_path: str = Field(default="", max_length=2000)
    discord_avatar_url: str = Field(default="", max_length=4000)


class CharacterCatalogPayload(_CatalogRecord):
    character_id: str = Field(min_length=1, max_length=200)
    player_id: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=200)
    gamertag: str = Field(default="", max_length=200)
    owned_skill_lines: tuple[str, ...] = ()
    passive_ranks: dict[str, int] = {}
    passive_cp_points: dict[str, int] = {}

    @field_validator("passive_ranks", "passive_cp_points")
    @classmethod
    def nonnegative_progression(cls, value: dict[str, int]) -> dict[str, int]:
        if any(points < 0 for points in value.values()):
            raise ValueError("progression values must be nonnegative")
        return value


class BuildCatalogPayload(_CatalogRecord):
    build_id: str = Field(min_length=1, max_length=200)
    character_id: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=300)
    legacy: dict[str, Any] = {}
    payload: dict[str, Any] = {}
    build_kind: str = Field(default="saved", max_length=80)
    source: dict[str, Any] = {}


class TeamAssignmentCatalogPayload(_CatalogRecord):
    assignment_id: str = Field(min_length=1, max_length=240)
    team_name: str = Field(min_length=1, max_length=240)
    build_id: str = Field(min_length=1, max_length=200)
    raid_role: str = Field(default="", max_length=80)
    slot_name: str = Field(default="", max_length=120)
    status: str = Field(default="Active", max_length=80)
    notes: str = Field(default="", max_length=4000)


class UserBuildCatalogPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: int
    players: list[PlayerCatalogPayload] = Field(default_factory=list)
    characters: list[CharacterCatalogPayload] = Field(default_factory=list)
    builds: list[BuildCatalogPayload] = Field(default_factory=list)
    team_assignments: list[TeamAssignmentCatalogPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identity_graph(self) -> "UserBuildCatalogPayload":
        if self.schema_version != 4:
            raise ValueError("canonical Build catalog schema_version must be 4")

        player_ids = [row.player_id for row in self.players]
        character_ids = [row.character_id for row in self.characters]
        build_ids = [row.build_id for row in self.builds]
        assignment_ids = [row.assignment_id for row in self.team_assignments]
        for label, values in (
            ("player_id", player_ids),
            ("character_id", character_ids),
            ("build_id", build_ids),
            ("assignment_id", assignment_ids),
        ):
            folded = [value.casefold() for value in values]
            if len(folded) != len(set(folded)):
                raise ValueError(f"duplicate canonical {label}")

        known_players = {value.casefold() for value in player_ids}
        known_characters = {value.casefold() for value in character_ids}
        known_builds = {value.casefold() for value in build_ids}
        for row in self.characters:
            if row.player_id.casefold() not in known_players:
                raise ValueError(
                    f"character {row.character_id!r} references unknown player {row.player_id!r}"
                )
        for row in self.builds:
            if row.character_id.casefold() not in known_characters:
                raise ValueError(
                    f"build {row.build_id!r} references unknown character {row.character_id!r}"
                )
        for row in self.team_assignments:
            if row.build_id.casefold() not in known_builds:
                raise ValueError(
                    f"team assignment {row.assignment_id!r} references unknown build {row.build_id!r}"
                )
        return self


def validate_user_build_catalog_payload(raw: Any) -> dict[str, Any]:
    return UserBuildCatalogPayload.model_validate(raw).model_dump(mode="json")


__all__ = [
    "UserBuildCatalogPayload",
    "ValidationError",
    "validate_user_build_catalog_payload",
]
