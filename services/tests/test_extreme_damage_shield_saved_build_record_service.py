from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_damage_shield_saved_build_record_service import (
    ExtremeDamageShieldSavedBuildRecordService,
)


class _Progression:
    def resolve(self, _build):
        return SimpleNamespace(
            resolved=True,
            unresolved=(),
            character_id="char-1",
            progression=SimpleNamespace(),
        )


class _ContextFactory:
    def build(self, **kwargs):
        assert kwargs["character_id"] == "char-1"
        assert kwargs["active_bar"] == "front"
        return SimpleNamespace(unresolved_gear_effects=("fixture gear gap",))


class _Optimizer:
    def __init__(self):
        self.context_factory = _ContextFactory()
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=SimpleNamespace())
        )


class _Coefficients:
    def resolve_name(self, name):
        mapping = {
            "Ward A": SimpleNamespace(rank=SimpleNamespace(entity_id="ward_a"), unresolved=()),
            "Damage Skill": SimpleNamespace(rank=SimpleNamespace(entity_id="damage"), unresolved=()),
            "Ward B": SimpleNamespace(rank=SimpleNamespace(entity_id="ward_b"), unresolved=()),
        }
        return mapping.get(
            name,
            SimpleNamespace(rank=None, unresolved=(f"{name}: unresolved",)),
        )


class _Events:
    def __init__(self):
        self.tooltip_service = SimpleNamespace(coefficients=_Coefficients())

    def evaluate(self, *, build, context, entity_id):
        assert build is not None
        assert context.unresolved_gear_effects == ("fixture gear gap",)
        if entity_id == "ward_a":
            return SimpleNamespace(
                modified_shield=5000.0,
                coefficient_number=1,
                unresolved=(),
            )
        if entity_id == "ward_b":
            return SimpleNamespace(
                modified_shield=7200.0,
                coefficient_number=2,
                unresolved=("ward B modifier gap",),
            )
        return SimpleNamespace(
            modified_shield=None,
            coefficient_number=None,
            unresolved=("damage: no SHIELD-classified coefficient component",),
        )


def _build():
    return SimpleNamespace(
        BuildId="build-1",
        BuildName="Fixture",
        FrontBarSkills=["Ward A", "Damage Skill", "Ward B", "", "", ""],
        BackBarSkills=[],
    )


def test_saved_build_shield_record_ranks_only_resolved_shield_skills() -> None:
    service = ExtremeDamageShieldSavedBuildRecordService(
        "unused.db",
        optimizer=_Optimizer(),
        event_service=_Events(),
        progression_adapter=_Progression(),
    )

    result = service.evaluate(_build(), active_bar="front")

    assert result.skill_name == "Ward B"
    assert result.entity_id == "ward_b"
    assert result.value == pytest.approx(7200.0)
    assert "Ward A: 5000 reviewed single shield from coefficient 1" in result.evidence
    assert "Ward B: 7200 reviewed single shield from coefficient 2" in result.evidence
    assert "damage: no SHIELD-classified coefficient component" not in result.unresolved
    assert "Build context: fixture gear gap" in result.unresolved
    assert "ward B modifier gap" in result.unresolved
    assert "Global shield-skill candidate search is not yet included" in result.unresolved


def test_saved_build_shield_record_reports_no_candidate_explicitly() -> None:
    build = _build()
    build.FrontBarSkills = ["Damage Skill", "", "", "", "", ""]
    service = ExtremeDamageShieldSavedBuildRecordService(
        "unused.db",
        optimizer=_Optimizer(),
        event_service=_Events(),
        progression_adapter=_Progression(),
    )

    result = service.evaluate(build, active_bar="front")

    assert result.value is None
    assert result.skill_name is None
    assert "No single SHIELD-classified skill was resolved on the saved front bar" in result.unresolved
