from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import SkillEffectKind
from services.extreme_damage_shield_event_service import (
    ExtremeDamageShieldEventService,
    ExtremeDamageShieldModifierInputs,
)


class _Components:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, _skill_rank_id):
        return self.rows


class _TooltipService:
    def __init__(self, *, classifications, traces, unresolved=()):
        self.components = _Components(classifications)
        self._traces = tuple(traces)
        self._unresolved = tuple(unresolved)

    def evaluate_entity_id(self, **_kwargs):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=42),
            components=self._traces,
            unresolved=self._unresolved,
        )


def _classification(number: int, kind: SkillEffectKind):
    return SimpleNamespace(
        coefficient_number=number,
        effect_kind=kind,
    )


def _trace(number: int, value: float):
    return SimpleNamespace(
        coefficient_number=number,
        final_value=value,
    )


def test_single_shield_component_reuses_coefficient_value_and_canonical_modifier_formula(tmp_path) -> None:
    tooltip = _TooltipService(
        classifications=(
            _classification(1, SkillEffectKind.SHIELD),
            _classification(2, SkillEffectKind.HEAL),
        ),
        traces=(
            _trace(1, 10000.0),
            _trace(2, 2500.0),
        ),
    )
    service = ExtremeDamageShieldEventService(
        tmp_path / "unused.db",
        tooltip_service=tooltip,
    )

    result = service.evaluate(
        build=SimpleNamespace(),
        context=SimpleNamespace(),
        entity_id="shield_fixture",
        modifiers=ExtremeDamageShieldModifierInputs(
            cp_damage_shield=0.10,
            set_damage_shield=0.20,
        ),
    )

    assert result.base_shield == pytest.approx(10000.0)
    assert result.modifier_bonus == pytest.approx((1.10 * 1.20) - 1.0)
    assert result.modified_shield == pytest.approx(13200.0)
    assert result.coefficient_number == 1
    assert result.mechanic_complete is True


def test_multiple_shield_components_fail_closed_without_event_identity(tmp_path) -> None:
    tooltip = _TooltipService(
        classifications=(
            _classification(1, SkillEffectKind.SHIELD),
            _classification(2, SkillEffectKind.SHIELD),
        ),
        traces=(
            _trace(1, 8000.0),
            _trace(2, 5000.0),
        ),
    )
    service = ExtremeDamageShieldEventService(
        tmp_path / "unused.db",
        tooltip_service=tooltip,
    )

    result = service.evaluate(
        build=SimpleNamespace(),
        context=SimpleNamespace(),
        entity_id="multi_shield_fixture",
    )

    assert result.modified_shield is None
    assert result.mechanic_complete is False
    assert any("explicit shield-event identity" in item for item in result.unresolved)


def test_missing_shield_classification_does_not_relabel_other_components(tmp_path) -> None:
    tooltip = _TooltipService(
        classifications=(_classification(1, SkillEffectKind.HEAL),),
        traces=(_trace(1, 9000.0),),
    )
    service = ExtremeDamageShieldEventService(
        tmp_path / "unused.db",
        tooltip_service=tooltip,
    )

    result = service.evaluate(
        build=SimpleNamespace(),
        context=SimpleNamespace(),
        entity_id="not_a_shield_fixture",
    )

    assert result.modified_shield is None
    assert any("no SHIELD-classified" in item for item in result.unresolved)
