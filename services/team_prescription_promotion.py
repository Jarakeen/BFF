from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.build_catalog_service import BuildCatalogService
from services.team_prescription import PrescribedRoster


def _identity(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


@dataclass(frozen=True)
class PrescribedBuildPromotion:
    slot_name: str
    character_id: str
    build_id: str
    build_name: str


def promote_prescribed_slot_to_character_build(
    *,
    catalog_service: BuildCatalogService,
    roster: PrescribedRoster,
    slot_name: str,
    character_id: str,
    build_name: str,
    replace_existing: bool = False,
) -> PrescribedBuildPromotion:
    """Save a generated team-slot snapshot as a new character-owned build.

    The prescription, character identity, and saved builds remain separate. This
    explicit promotion copies the immutable prescribed snapshot and never mutates
    another build such as ``DF Healer`` when creating ``GH Healer``.
    """

    normalized_slot = str(slot_name or "").strip()
    normalized_character_id = str(character_id or "").strip()
    normalized_build_name = str(build_name or "").strip()
    if not normalized_slot:
        raise ValueError("prescribed slot promotion requires a slot_name")
    if not normalized_character_id:
        raise ValueError("prescribed slot promotion requires a character_id")
    if not normalized_build_name:
        raise ValueError("prescribed slot promotion requires a new build_name")

    assignment = next(
        (
            item
            for item in roster.assignments
            if item.slot_name.casefold() == normalized_slot.casefold()
        ),
        None,
    )
    if assignment is None:
        raise ValueError(f"prescribed roster has no slot named {normalized_slot!r}")
    prescribed_build = assignment.prescribed_build
    if prescribed_build is None:
        raise ValueError(
            f"prescribed slot {assignment.slot_name!r} has no complete build snapshot"
        )

    character = catalog_service.get_character(normalized_character_id)
    if character is None:
        raise ValueError(f"canonical character not found: {normalized_character_id}")

    character_class = str(character.get("eso_class") or "").strip()
    character_race = str(character.get("race") or "").strip()
    if character_class and prescribed_build.EsoClass and _identity(
        character_class
    ) != _identity(prescribed_build.EsoClass):
        raise ValueError(
            f"prescribed class {prescribed_build.EsoClass} is incompatible with "
            f"character class {character_class}"
        )
    if character_race and prescribed_build.Race and _identity(character_race) != _identity(
        prescribed_build.Race
    ):
        raise ValueError(
            f"prescribed race {prescribed_build.Race} is incompatible with "
            f"character race {character_race}"
        )

    existing = next(
        (
            item
            for item in catalog_service.builds_for_character(normalized_character_id)
            if _identity(item.get("name")) == _identity(normalized_build_name)
        ),
        None,
    )
    if existing is not None and not replace_existing:
        raise ValueError(
            f"character already has a build named {normalized_build_name!r}; "
            "explicit replacement permission is required"
        )

    prescribed_build.Name = str(character.get("name") or "")
    prescribed_build.Gamertag = str(character.get("gamertag") or "")
    prescribed_build.EsoClass = character_class or prescribed_build.EsoClass
    prescribed_build.Race = character_race or prescribed_build.Race
    prescribed_build.BuildName = normalized_build_name
    payload: dict[str, Any] = prescribed_build.to_dict()
    payload["CharacterId"] = normalized_character_id

    record = catalog_service.upsert_build(
        character_id=normalized_character_id,
        build_name=normalized_build_name,
        payload=payload,
    )
    return PrescribedBuildPromotion(
        slot_name=assignment.slot_name,
        character_id=normalized_character_id,
        build_id=str(record["build_id"]),
        build_name=normalized_build_name,
    )
