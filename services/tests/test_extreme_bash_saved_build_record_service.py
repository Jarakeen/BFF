from __future__ import annotations

from types import SimpleNamespace

import pytest

import services.extreme_bash_saved_build_record_service as module
from services.extreme_bash_saved_build_record_service import (
    ExtremeBashSavedBuildRecordService,
)


class _Optimizer:
    def __init__(self) -> None:
        self.context_factory = SimpleNamespace()
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=SimpleNamespace())
        )


class _ProgressionAdapter:
    def __init__(self, _catalog) -> None:
        pass

    def resolve(self, _build):
        return SimpleNamespace(
            resolved=True,
            unresolved=(),
            progression=SimpleNamespace(),
            character_id="char-1",
        )


class _CPRepository:
    def __init__(self, _database_path) -> None:
        pass


class _GlyphRepository:
    def __init__(self, _database_path) -> None:
        pass


class _TraitRepository:
    def __init__(self, _database_path) -> None:
        pass


class _JewelryService:
    def __init__(self, _glyphs, _traits) -> None:
        pass

    def evaluate_build(self, _build):
        return SimpleNamespace(reviewed_item_extra_bash_damage=900.0)


class _DeadlyBashService:
    def __init__(self, _database_path) -> None:
        pass

    def resolve(self, _progression):
        return SimpleNamespace(rank=2)


class _ChampionPointService:
    @staticmethod
    def resolve_damage(_repository):
        return SimpleNamespace(stages=2)


class _ContextObjectiveService:
    @staticmethod
    def evaluate_build(*_args, **kwargs):
        assert kwargs["character_id"] == "char-1"
        assert kwargs["build_id"] == "build-1:extreme-bash"
        assert kwargs["active_bar"] == "back"
        return SimpleNamespace(
            reviewed_value=12345.0,
            mechanic_complete=False,
            physical_resistance=32100.0,
            spell_resistance=31500.0,
            context_blockers=("fixture context gap",),
            objective=SimpleNamespace(
                source_blockers=("fixture source gap",),
                objective=SimpleNamespace(
                    unresolved_channels=("buff_extra_bash_damage",),
                    legality_blockers=(),
                ),
            ),
        )


def _patch_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _ProgressionAdapter)
    monkeypatch.setattr(module, "ChampionPointStaticRepository", _CPRepository)
    monkeypatch.setattr(module, "JewelryGlyphEffectRepository", _GlyphRepository)
    monkeypatch.setattr(module, "JewelryTraitRepository", _TraitRepository)
    monkeypatch.setattr(module, "ExtremeBashJewelryService", _JewelryService)
    monkeypatch.setattr(module, "ExtremeDeadlyBashService", _DeadlyBashService)
    monkeypatch.setattr(module, "ExtremeBashChampionPointService", _ChampionPointService)
    monkeypatch.setattr(module, "ExtremeBashContextObjectiveService", _ContextObjectiveService)


def test_saved_build_bash_record_composes_existing_owners_and_preserves_blockers(monkeypatch) -> None:
    _patch_dependencies(monkeypatch)
    service = ExtremeBashSavedBuildRecordService(
        "unused.db",
        optimizer=_Optimizer(),
    )
    build = SimpleNamespace(BuildId="build-1", BuildName="Fixture")

    result = service.evaluate(build, active_bar="back")

    assert result.value == pytest.approx(12345.0)
    assert result.mechanic_complete is False
    assert "Physical Resistance: 32100" in result.evidence
    assert "Spell Resistance: 31500" in result.evidence
    assert "Bashing Brutality stages: 2" in result.evidence
    assert "Equipped jewelry Bash bonus: 900" in result.evidence
    assert "Deadly Bash rank: 2" in result.evidence
    assert result.unresolved == (
        "fixture context gap",
        "fixture source gap",
        "Bash formula channel unresolved: buff_extra_bash_damage",
    )


def test_saved_build_bash_record_rejects_unresolved_progression(monkeypatch) -> None:
    _patch_dependencies(monkeypatch)

    class _BlockedProgressionAdapter(_ProgressionAdapter):
        def resolve(self, _build):
            return SimpleNamespace(
                resolved=False,
                unresolved=("character progression unresolved",),
                progression=None,
                character_id="",
            )

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _BlockedProgressionAdapter)
    service = ExtremeBashSavedBuildRecordService(
        "unused.db",
        optimizer=_Optimizer(),
    )

    with pytest.raises(ValueError, match="character progression unresolved"):
        service.evaluate(SimpleNamespace(BuildId="build-1", BuildName="Fixture"))
