from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.saved_build_capability_service import SavedBuildCapabilityService


def _write_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                ability_id INTEGER,
                name TEXT,
                class_type TEXT,
                rank INTEGER,
                morph INTEGER,
                is_crafted INTEGER
            );
            INSERT INTO ability(ability_id, name, class_type, rank, morph, is_crafted) VALUES
                (1001, 'Combat Prayer', 'Templar', 4, 2, 0),
                (1002, 'Combat Prayer', 'Warden', 4, 2, 0),
                (1003, 'Energy Orb', '', 4, 2, 0),
                (4001, 'Ulfsilds Contingency', '', 1, 0, 1);
            """
        )


def _service(path: Path) -> SavedBuildCapabilityService:
    builds = SimpleNamespace(canonical=SimpleNamespace(catalog_service=object()))
    placeholder = object()
    return SavedBuildCapabilityService(
        builds,
        path,
        context_factory=placeholder,
        progression=placeholder,
        skills=placeholder,
        gear=placeholder,
        potions=placeholder,
    )


class _CountingProgression:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, build: PlayerBuild):
        self.calls += 1
        return SimpleNamespace(
            unresolved=(),
            character_id=f"character:{build.Name or 'anonymous'}",
            progression=SimpleNamespace(),
        )


class _CountingContextFactory:
    def __init__(self) -> None:
        self.calls = 0

    def build(self, **_kwargs):
        self.calls += 1
        return SimpleNamespace(unresolved_gear_effects=())


class _NoopSkills:
    def resolve(self, _ability_id: int):
        return ()


class _NoopGear:
    def resolve(self, *_args, **_kwargs):
        return ()


class _NoopPotions:
    def resolve(self, _name: str):
        return SimpleNamespace(unresolved=(), effects=())


def _audit_service(path: Path):
    builds = SimpleNamespace(canonical=SimpleNamespace(catalog_service=object()))
    progression = _CountingProgression()
    context_factory = _CountingContextFactory()
    service = SavedBuildCapabilityService(
        builds,
        path,
        context_factory=context_factory,
        progression=progression,
        skills=_NoopSkills(),
        gear=_NoopGear(),
        potions=_NoopPotions(),
    )
    return service, progression, context_factory


def test_ability_id_cache_reuses_same_name_and_class(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_id(" Combat Prayer ", "Templar") == 1001

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE ability SET ability_id=2001 WHERE name='Combat Prayer' AND class_type='Templar'"
        )

    assert service._ability_id("combat prayer", " templar ") == 1001
    assert service._ability_id("Combat Prayer", "Warden") == 1002


def test_unresolved_ability_id_is_cached_for_service_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_id("Missing Skill", "Templar") is None

    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO ability(ability_id, name, class_type, rank, morph, is_crafted) "
            "VALUES (3001, 'Missing Skill', 'Templar', 4, 2, 0)"
        )

    assert service._ability_id(" missing skill ", "templar") is None
    assert _service(path)._ability_id("Missing Skill", "Templar") == 3001


def test_crafted_ability_check_is_cached_for_service_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_is_crafted(4001) is True

    with sqlite3.connect(path) as db:
        db.execute("UPDATE ability SET is_crafted=0 WHERE ability_id=4001")

    assert service._ability_is_crafted(4001) is True
    assert _service(path)._ability_is_crafted(4001) is False


def test_noncrafted_ability_check_is_cached_for_service_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_is_crafted(1001) is False

    with sqlite3.connect(path) as db:
        db.execute("UPDATE ability SET is_crafted=1 WHERE ability_id=1001")

    assert service._ability_is_crafted(1001) is False
    assert _service(path)._ability_is_crafted(1001) is True


def test_identical_build_content_reuses_cached_capability_audit(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service, progression, context_factory = _audit_service(path)
    first_build = PlayerBuild(Name="Magrat", BuildName="DF Healer", EsoClass="Warden")
    second_build = PlayerBuild.from_dict(first_build.to_dict())

    first = service.audit_build(first_build)
    second = service.audit_build(second_build)

    assert second is first
    assert progression.calls == 1
    assert context_factory.calls == 2


def test_candidate_family_changes_force_fresh_capability_audits(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service, progression, context_factory = _audit_service(path)
    baseline = PlayerBuild(Name="Magrat", BuildName="DF Healer", EsoClass="Warden")

    variants: list[PlayerBuild] = []

    mundus = PlayerBuild.from_dict(baseline.to_dict())
    mundus.Mundus = "The Ritual"
    variants.append(mundus)

    food = PlayerBuild.from_dict(baseline.to_dict())
    food.Food = "Bewitched Sugar Skulls"
    variants.append(food)

    trait = PlayerBuild.from_dict(baseline.to_dict())
    trait.Armor["Head"]["Trait"] = "Divines"
    variants.append(trait)

    enchant = PlayerBuild.from_dict(baseline.to_dict())
    enchant.Armor["Head"]["Enchant"] = "Max Magicka"
    variants.append(enchant)

    service.audit_build(baseline)
    for candidate in variants:
        service.audit_build(candidate)

    assert progression.calls == 5
    assert context_factory.calls == 10
    assert len(service._audit_cache) == 5


def test_build_identity_is_part_of_capability_audit_cache_key(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service, _, _ = _audit_service(path)
    magrat = PlayerBuild(Name="Magrat", BuildName="Shared Name", EsoClass="Warden")
    susan = PlayerBuild(Name="Susan", BuildName="Shared Name", EsoClass="Warden")

    assert service._build_cache_key(magrat) != service._build_cache_key(susan)


def test_capability_audit_cache_is_service_instance_scoped(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", EsoClass="Warden")
    first_service, first_progression, _ = _audit_service(path)
    second_service, second_progression, _ = _audit_service(path)

    first_service.audit_build(build)
    second_service.audit_build(PlayerBuild.from_dict(build.to_dict()))

    assert first_progression.calls == 1
    assert second_progression.calls == 1
    assert first_service._audit_cache is not second_service._audit_cache


def test_cached_scribed_skill_audit_preserves_fail_closed_boundary(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service, progression, context_factory = _audit_service(path)
    build = PlayerBuild(
        Name="Magrat",
        BuildName="Scribing Check",
        EsoClass="Warden",
        FrontBarSkills=["Ulfsilds Contingency", "", "", "", "", ""],
    )

    first = service.audit_build(build)
    second = service.audit_build(PlayerBuild.from_dict(build.to_dict()))

    expected = (
        "front scribed skill requires configured recipe semantics before capability resolution: "
        "Ulfsilds Contingency"
    )
    assert expected in first.capability_unresolved
    assert second is first
    assert second.capability_unresolved == first.capability_unresolved
    assert progression.calls == 1
    assert context_factory.calls == 2
