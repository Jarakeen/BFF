from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationActionKind
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
    rotation_plan_from_artifact,
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


def test_restores_saved_artifact_into_canonical_rotation_plan(tmp_path) -> None:
    service = BuildRotationArtifactService(tmp_path / "build_rotations.json")
    service.save_rotation(
        build_id="magrat-df",
        artifact={
            "character_name": "Magrat",
            "build_name": "DF Healer",
            "duration_seconds": 30.0,
            "actions": [
                {
                    "time_seconds": 0.0,
                    "sequence": 0,
                    "kind": "skill",
                    "name": "Combat Prayer",
                    "bar": "front",
                },
                {
                    "time_seconds": 1.0,
                    "sequence": 0,
                    "kind": "light_attack",
                    "name": None,
                    "bar": "front",
                },
            ],
            "assumptions": ["reviewed plan"],
            "unresolved": ["one explicit gap"],
        },
    )

    plan = service.get_rotation_plan("magrat-df")

    assert plan is not None
    assert plan.character_name == "Magrat"
    assert plan.build_name == "DF Healer"
    assert plan.duration_seconds == 30.0
    assert tuple(action.kind for action in plan.actions) == (
        RotationActionKind.SKILL,
        RotationActionKind.LIGHT_ATTACK,
    )
    assert plan.assumptions == ("reviewed plan",)
    assert plan.unresolved == ("one explicit gap",)


def test_saved_rotation_restoration_fails_closed_on_invalid_action() -> None:
    with pytest.raises(ValueError, match="action 0 is invalid"):
        rotation_plan_from_artifact(
            {
                "character_name": "Magrat",
                "build_name": "DF Healer",
                "duration_seconds": 30.0,
                "actions": [
                    {
                        "time_seconds": 0.0,
                        "sequence": 0,
                        "kind": "invented_action",
                        "name": "Definitely Real Skill",
                        "bar": "front",
                    }
                ],
            }
        )


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


def test_resolve_canonical_build_id_prefers_explicit_stable_id(tmp_path: Path) -> None:
    catalog = BuildCatalogService(tmp_path / "characters.json")
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="SW Healer",
        BuildId="build-explicit",
    )
    payload = catalog.new_catalog()
    payload["builds"] = [
        {
            "build_id": "build-explicit",
            "character_id": "char-1",
            "name": "Different Display Name",
            "legacy": {"Name": "Elsewhere", "Gamertag": "SomeoneElse", "BuildName": "Other"},
            "payload": {"Name": "Elsewhere", "Gamertag": "SomeoneElse", "BuildName": "Other"},
        }
    ]
    catalog.save(payload)

    assert resolve_canonical_build_id(catalog, build) == "build-explicit"


def test_resolve_canonical_build_id_fails_closed_on_stale_explicit_id(tmp_path: Path) -> None:
    catalog = BuildCatalogService(tmp_path / "characters.json")
    source = PlayerBuild(Name="Magrat", Gamertag="Jarakeen", BuildName="SW Healer")
    payload = catalog.import_legacy_roster(BuildRoster(Members=[source]))
    catalog.save(payload)

    stale = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="SW Healer",
        BuildId="missing-build-id",
    )
    assert resolve_canonical_build_id(catalog, stale) is None
