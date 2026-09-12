from __future__ import annotations

from types import SimpleNamespace

from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
)


class _Catalog:
    def __init__(self, builds):
        self._builds = builds

    def load(self):
        return {"builds": self._builds}


def test_rotation_artifacts_are_isolated_by_canonical_build_id(tmp_path) -> None:
    service = BuildRotationArtifactService(tmp_path / "build_rotations.json")

    service.save_rotation(
        build_id="magrat-df",
        artifact={"character_name": "Magrat", "actions": [{"name": "Combat Prayer"}]},
    )
    service.save_rotation(
        build_id="magrat-rojo",
        artifact={"character_name": "Magrat", "actions": [{"name": "Energy Orb"}]},
    )

    assert service.get_rotation("magrat-df")["actions"][0]["name"] == "Combat Prayer"
    assert service.get_rotation("magrat-rojo")["actions"][0]["name"] == "Energy Orb"
    assert service.has_rotation("magrat-df") is True
    assert service.has_rotation("missing") is False


def test_saving_again_replaces_only_that_builds_rotation(tmp_path) -> None:
    service = BuildRotationArtifactService(tmp_path / "build_rotations.json")
    service.save_rotation(build_id="build-1", artifact={"actions": [{"name": "First"}]})
    service.save_rotation(build_id="build-2", artifact={"actions": [{"name": "Other"}]})

    service.save_rotation(build_id="build-1", artifact={"actions": [{"name": "Updated"}]})

    assert service.get_rotation("build-1")["actions"] == [{"name": "Updated"}]
    assert service.get_rotation("build-2")["actions"] == [{"name": "Other"}]


def test_resolver_uses_gamertag_character_and_build_identity() -> None:
    catalog = _Catalog(
        [
            {
                "build_id": "jarakeen-magrat-df",
                "name": "DF Healer",
                "payload": {
                    "Gamertag": "Jarakeen",
                    "Name": "Magrat",
                    "BuildName": "DF Healer",
                },
            },
            {
                "build_id": "jarakeen-magrat-rojo",
                "name": "RoJo Healer",
                "payload": {
                    "Gamertag": "Jarakeen",
                    "Name": "Magrat",
                    "BuildName": "RoJo Healer",
                },
            },
        ]
    )
    build = SimpleNamespace(Gamertag="Jarakeen", Name="Magrat", BuildName="RoJo Healer")

    assert resolve_canonical_build_id(catalog, build) == "jarakeen-magrat-rojo"


def test_ambiguous_name_only_match_is_not_guessed() -> None:
    catalog = _Catalog(
        [
            {
                "build_id": "one",
                "name": "Trial",
                "payload": {"Gamertag": "One", "Name": "Same", "BuildName": "Trial"},
            },
            {
                "build_id": "two",
                "name": "Trial",
                "payload": {"Gamertag": "Two", "Name": "Same", "BuildName": "Trial"},
            },
        ]
    )
    build = SimpleNamespace(Gamertag="", Name="Same", BuildName="Trial")

    assert resolve_canonical_build_id(catalog, build) is None
