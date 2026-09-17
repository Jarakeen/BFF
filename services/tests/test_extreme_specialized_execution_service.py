from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_specialized_execution_service import (
    ExtremeSpecializedExecutionService,
)


class _HealingEvents:
    def evaluate(self, _build, objective_key, *, active_bar="front"):
        assert objective_key in {"actual_heal", "critical_heal"}
        assert active_bar == "back"
        winner = SimpleNamespace(
            candidate=SimpleNamespace(name="Fixture Heal"),
            route=SimpleNamespace(
                base_class=SimpleNamespace(value="warden"),
                equipped_skill_lines=("Green Balance", "Winter's Embrace", "Animal Companions"),
            ),
            slotted_index=2,
            unresolved=("fixture unresolved",),
        )
        catalog = SimpleNamespace(
            best_scored=winner,
            search_scope=("shared H1 search",),
            omitted_scope=("fixture omitted",),
        )
        return SimpleNamespace(
            catalog=catalog,
            best_scored_value=54321.0,
            mechanic_complete=False,
            global_maximum_proven=False,
        )


class _BashRecord:
    def evaluate(self, _build, *, active_bar="front"):
        assert active_bar == "back"
        return SimpleNamespace(
            value=12345.0,
            mechanic_complete=False,
            evidence=("Bashing Brutality stages: 2", "Equipped jewelry Bash bonus: 900"),
            unresolved=("Bash formula channel unresolved: buff_extra_bash_damage",),
        )


class _MovementPackage:
    def evaluate(self, objective_key):
        assert objective_key in {"movement_speed", "sprint_speed", "stealthed_movement_speed"}
        return SimpleNamespace(
            result=SimpleNamespace(
                raw_multiplier=1.41,
                effective_multiplier=1.41,
                effective_cap_multiplier=2.0,
            ),
            mechanic_complete=False,
            evidence=("reviewed static movement package",),
            unresolved=("runtime movement providers not yet exhaustive",),
        )


class _StealthPackage:
    def evaluate(self):
        return SimpleNamespace(
            realization=SimpleNamespace(
                set_names=("Night Terror", "Night Mother's Embrace"),
                counts=(3, 5),
                weapon_shape=SimpleNamespace(value="two_handed"),
            ),
            reviewed_flat_reduction_meters=4.0,
            mechanic_complete=False,
            gear_denominator_proven=True,
            evidence=(
                "Night Terror (3): 2 m reviewed detection-radius reduction",
                "Night Mother's Embrace (5): 2 m reviewed detection-radius reduction",
            ),
            unresolved=("final stealth stacking unresolved",),
        )


def _service() -> ExtremeSpecializedExecutionService:
    return ExtremeSpecializedExecutionService(
        healing_events=_HealingEvents(),
        bash_record=_BashRecord(),
        movement_package=_MovementPackage(),
        stealth_package=_StealthPackage(),
    )


def test_current_direct_specialized_routes_are_explicit() -> None:
    for key in (
        "actual_heal",
        "critical_heal",
        "bash_damage",
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
    ):
        assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)
    assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("damage_shield")


def test_saved_build_direct_routes_are_explicit() -> None:
    for key in ("actual_heal", "critical_heal", "bash_damage"):
        assert ExtremeSpecializedExecutionService.requires_saved_build(key)
    for key in (
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
    ):
        assert not ExtremeSpecializedExecutionService.requires_saved_build(key)


def test_objective_specific_requirements_can_diverge_within_one_family() -> None:
    assert ExtremeSpecializedExecutionService.requirements_for("bash_damage") == ()
    shield = ExtremeSpecializedExecutionService.requirements_for("damage_shield")
    assert tuple(row.key for row in shield) == ("event_source",)

    sustain = ExtremeSpecializedExecutionService.requirements_for("resource_sustain")
    ultimate = ExtremeSpecializedExecutionService.requirements_for("ultimate_generation")
    assert sustain == ultimate
    assert tuple(row.key for row in sustain) == ("duration_seconds", "timeline_evidence")

    movement = ExtremeSpecializedExecutionService.requirements_for("movement_speed")
    sprint = ExtremeSpecializedExecutionService.requirements_for("sprint_speed")
    stealth_move = ExtremeSpecializedExecutionService.requirements_for("stealthed_movement_speed")
    assert movement == sprint == stealth_move == ()
    assert ExtremeSpecializedExecutionService.requirements_for("detection_radius_reduction") == ()

    invis_duration = ExtremeSpecializedExecutionService.requirements_for("invisibility_duration")
    invis_uptime = ExtremeSpecializedExecutionService.requirements_for("invisibility_uptime")
    assert invis_duration == invis_uptime
    assert tuple(row.key for row in invis_duration) == ("duration_seconds", "invisibility_windows")


def test_heal_event_execution_normalizes_family_result_for_ui() -> None:
    result = _service().execute(SimpleNamespace(), "actual_heal", active_bar="back")

    assert result.value == pytest.approx(54321.0)
    assert result.value_text == "54,321"
    assert ("Heal", "Fixture Heal") in result.summary_rows
    assert result.unresolved == ("fixture unresolved",)


def test_saved_build_direct_execution_rejects_missing_build() -> None:
    for key in ("actual_heal", "bash_damage"):
        with pytest.raises(ValueError, match="requires a saved-build starting context"):
            _service().execute(None, key)


def test_bash_execution_normalizes_saved_build_lower_bound() -> None:
    result = _service().execute(SimpleNamespace(), "bash_damage", active_bar="back")

    assert result.execution_family == "single-event-output"
    assert result.value == pytest.approx(12345.0)
    assert result.value_text == "12,345"
    assert result.mechanic_complete is False
    assert ("Active bar", "back") in result.summary_rows
    assert ("Reviewed Bash lower bound", "12,345") in result.summary_rows
    assert result.search_scope == (
        "Bashing Brutality stages: 2",
        "Equipped jewelry Bash bonus: 900",
    )


def test_movement_execution_normalizes_reviewed_lower_bound_without_saved_build() -> None:
    result = _service().execute(None, "movement_speed")

    assert result.value == pytest.approx(1.41)
    assert result.value_text == "141.0%"
    assert ("Effective cap", "200%") in result.summary_rows


def test_stealth_execution_normalizes_legal_gear_lower_bound_without_saved_build() -> None:
    result = _service().execute(None, "detection_radius_reduction")

    assert result.value == pytest.approx(4.0)
    assert result.value_text == "4 m reviewed gear reduction"
    assert ("Gear denominator proven", "YES") in result.summary_rows
    assert ("Gear sets", "Night Terror, Night Mother's Embrace") in result.summary_rows


def test_damage_shield_still_names_its_missing_event_source() -> None:
    with pytest.raises(
        ValueError,
        match="requires family-specific scenario inputs before execution: Event Source",
    ):
        _service().execute(SimpleNamespace(), "damage_shield")
