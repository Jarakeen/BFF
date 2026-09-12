from __future__ import annotations

import pytest

from models.build_model import ARMOR_SLOTS
from services.character_creation_service import (
    CharacterCreationRequest,
    CharacterCreationService,
)


class _WeightResolver:
    def __init__(self, value: str | None) -> None:
        self.value = value
        self.calls: list[str] = []

    def resolve(self, set_name: str) -> str | None:
        self.calls.append(set_name)
        return self.value


def test_create_builds_default_character_and_assigns_starter_sets():
    build = CharacterCreationService().create(
        CharacterCreationRequest(
            name="Magrat",
            eso_class="Warden",
            race="Breton",
            role="Healer",
            gamertag="Jarakeen",
            alliance="Daggerfall Covenant",
            body_set="Spell Power Cure",
            weapons_jewelry_set="Powerful Assault",
        )
    )

    assert build.Name == "Magrat"
    assert build.Gamertag == "Jarakeen"
    assert build.BuildName == "Default"
    assert build.EsoClass == "Warden"
    assert build.Race == "Breton"
    assert build.Role == "Healer"
    assert build.Alliance == "Daggerfall Covenant"
    assert all(build.Armor[slot]["Set"] == "Spell Power Cure" for slot in ARMOR_SLOTS)
    assert build.FrontBarWeapon.Set == "Powerful Assault"
    assert build.BackBarWeapon.Set == "Powerful Assault"
    assert build.Necklace.Set == "Powerful Assault"
    assert build.Ring1.Set == "Powerful Assault"
    assert build.Ring2.Set == "Powerful Assault"


def test_create_autofills_unambiguous_body_set_weight():
    resolver = _WeightResolver("Light")
    build = CharacterCreationService(resolver).create(
        CharacterCreationRequest(
            name="Magrat",
            eso_class="Warden",
            race="Breton",
            role="Healer",
            body_set="Spell Power Cure",
        )
    )

    assert resolver.calls == ["Spell Power Cure"]
    assert all(build.Armor[slot]["Weight"] == "Light" for slot in ARMOR_SLOTS)


def test_create_leaves_weight_blank_when_body_set_is_not_single_weight():
    build = CharacterCreationService(_WeightResolver(None)).create(
        CharacterCreationRequest(
            name="Flexible Toon",
            eso_class="Warden",
            race="Breton",
            role="Healer",
            body_set="Flexible Set",
        )
    )

    assert all(build.Armor[slot]["Weight"] == "" for slot in ARMOR_SLOTS)


def test_create_allows_optional_fields_and_sets_to_be_blank():
    build = CharacterCreationService().create(
        CharacterCreationRequest(
            name="New Toon",
            eso_class="Templar",
            race="High Elf",
            role="Damage Dealer",
        )
    )

    assert build.BuildName == "Default"
    assert build.Gamertag == ""
    assert build.Alliance == ""
    assert all(not build.Armor[slot]["Set"] for slot in ARMOR_SLOTS)
    assert build.FrontBarWeapon.Set == ""
    assert build.Necklace.Set == ""


def test_create_requires_identity_fields():
    with pytest.raises(ValueError, match="Character name"):
        CharacterCreationService().create(
            CharacterCreationRequest(
                name="",
                eso_class="Warden",
                race="Breton",
                role="Healer",
            )
        )


def test_create_rejects_vampire_and_werewolf_together():
    with pytest.raises(ValueError, match="both Vampire and Werewolf"):
        CharacterCreationService().create(
            CharacterCreationRequest(
                name="Impossible Toon",
                eso_class="Warden",
                race="Breton",
                role="Healer",
                vampire=True,
                werewolf=True,
            )
        )
