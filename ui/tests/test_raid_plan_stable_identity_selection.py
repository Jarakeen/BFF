from types import SimpleNamespace

from ui.raid_plan_persistence_page import RaidPlanPersistencePage
from ui.raid_plan_stable_identity_selection_page import (
    RaidPlanStableIdentitySelectionPage,
    stable_character_id_for_name,
    stable_player_id_for_name,
)


class _Catalog:
    def __init__(self):
        self.characters = {
            "character-magrat": {
                "character_id": "character-magrat",
                "player_id": "player-jara",
                "name": "Magrat",
            },
            "character-nanny": {
                "character_id": "character-nanny",
                "player_id": "player-jara",
                "name": "Nanny",
            },
            "character-rylo": {
                "character_id": "character-rylo",
                "player_id": "player-rylo",
                "name": "Rylonia",
            },
        }

    def characters_for_player(self, player_id):
        return [
            dict(row)
            for row in self.characters.values()
            if row["player_id"] == player_id
        ]

    def get_character(self, character_id):
        row = self.characters.get(character_id)
        return dict(row) if row is not None else None


def _personnel(
    *,
    player,
    character="",
    player_id="",
    character_id="",
):
    return SimpleNamespace(
        PlayerName=player,
        CharacterName=character,
        CanonicalPlayerId=player_id,
        CanonicalCharacterId=character_id,
    )


def _build(*, player, character, character_id=""):
    return SimpleNamespace(
        Gamertag=player,
        Name=character,
        CharacterId=character_id,
    )


def test_player_picker_identity_allows_multiple_character_rows_for_one_player() -> None:
    personnel = [
        _personnel(
            player="Jarakeen",
            character="Magrat",
            player_id="player-jara",
            character_id="character-magrat",
        ),
        _personnel(
            player="jarakeen",
            character="Nanny",
            player_id="player-jara",
            character_id="character-nanny",
        ),
    ]

    assert stable_player_id_for_name(personnel, "JARAKEEN") == "player-jara"


def test_player_picker_identity_fails_closed_on_conflicting_explicit_ids() -> None:
    personnel = [
        _personnel(player="Same Name", player_id="player-a"),
        _personnel(player="same name", player_id="player-b"),
    ]

    assert stable_player_id_for_name(personnel, "Same Name") is None


def test_character_picker_identity_comes_from_canonical_player_character_records() -> None:
    catalog = _Catalog()

    assert stable_character_id_for_name(
        [],
        [],
        "Jarakeen",
        "Magrat",
        player_id="player-jara",
        catalog_service=catalog,
    ) == "character-magrat"


def test_character_picker_identity_rejects_character_owned_by_other_player() -> None:
    catalog = _Catalog()
    builds = [
        _build(
            player="Jarakeen",
            character="Rylonia",
            character_id="character-rylo",
        )
    ]

    assert stable_character_id_for_name(
        builds,
        [],
        "Jarakeen",
        "Rylonia",
        player_id="player-jara",
        catalog_service=catalog,
    ) is None


def test_character_picker_identity_fails_closed_when_explicit_sources_conflict() -> None:
    catalog = _Catalog()
    personnel = [
        _personnel(
            player="Jarakeen",
            character="Magrat",
            player_id="player-jara",
            character_id="character-nanny",
        )
    ]

    assert stable_character_id_for_name(
        [],
        personnel,
        "Jarakeen",
        "Magrat",
        player_id="player-jara",
        catalog_service=catalog,
    ) is None


def test_persisted_raid_plan_page_uses_stable_identity_picker_layer() -> None:
    assert issubclass(RaidPlanPersistencePage, RaidPlanStableIdentitySelectionPage)
