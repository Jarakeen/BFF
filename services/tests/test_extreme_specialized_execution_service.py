from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_specialized_execution_service import ExtremeSpecializedExecutionService


class _HealingEvents:
    def evaluate(self, _build, objective_key, *, active_bar="front"):
        winner = SimpleNamespace(
            candidate=SimpleNamespace(name="Fixture Heal"),
            route=SimpleNamespace(base_class=SimpleNamespace(value="warden"), equipped_skill_lines=("Green Balance",)),
            slotted_index=2,
            unresolved=("fixture unresolved",),
        )
        return SimpleNamespace(
            catalog=SimpleNamespace(best_scored=winner, search_scope=("shared H1 search",), omitted_scope=("fixture omitted",)),
            best_scored_value=54321.0,
            mechanic_complete=False,
            global_maximum_proven=False,
        )


class _ShieldRecord:
    def evaluate(self, _build, *, active_bar="front"):
        return SimpleNamespace(
            skill_name="Hardened Ward",
            entity_id="hardened_ward",
            value=15000.0,
            mechanic_complete=False,
            evidence=("Hardened Ward: 15000 reviewed single shield from coefficient 1",),
            unresolved=("Global shield-skill candidate search is not yet included",),
        )


class _BashRecord:
    def evaluate(self, _build, *, active_bar="front"):
        return SimpleNamespace(
            value=12345.0,
            mechanic_complete=False,
            evidence=("Bashing Brutality stages: 2",),
            unresolved=("Bash formula channel unresolved",),
        )


class _MovementPackage:
    def evaluate(self, objective_key):
        return SimpleNamespace(
            result=SimpleNamespace(raw_multiplier=1.41, effective_multiplier=1.41, effective_cap_multiplier=2.0),
            mechanic_complete=False,
            evidence=("reviewed static movement package",),
            unresolved=("runtime movement providers not yet exhaustive",),
        )


class _StealthPackage:
    def evaluate(self):
        return SimpleNamespace(
            realization=SimpleNamespace(set_names=("Night Terror",), counts=(3,), weapon_shape=SimpleNamespace(value="two_handed")),
            reviewed_flat_reduction_meters=2.0,
            mechanic_complete=False,
            gear_denominator_proven=True,
            evidence=("Night Terror (3): 2 m reviewed detection-radius reduction",),
            unresolved=("final stealth stacking unresolved",),
        )


class _InvisibilityDurationRecord:
    def evaluate(self):
        return SimpleNamespace(
            provider=SimpleNamespace(name="Prowler's Talisman"),
            duration_seconds=10.0,
            mechanic_complete=False,
            evidence=("Prowler's Talisman 1pc: 10s invisibility",),
            unresolved=("Invisibility provider corpus is not yet exhaustive",),
        )


class _InvisibilityUptimeRecord:
    def evaluate(self, *, duration_seconds):
        return SimpleNamespace(
            provider=SimpleNamespace(name="Prowler's Talisman"),
            duration_seconds=float(duration_seconds),
            covered_seconds=30.0,
            uptime_ratio=0.30,
            window_count=3,
            mechanic_complete=False,
            evidence=("constructive Prowler recurrence",),
            unresolved=("Invisibility provider corpus is not yet exhaustive",),
        )


def _service():
    return ExtremeSpecializedExecutionService(
        healing_events=_HealingEvents(),
        shield_record=_ShieldRecord(),
        bash_record=_BashRecord(),
        movement_package=_MovementPackage(),
        stealth_package=_StealthPackage(),
        invisibility_duration_record=_InvisibilityDurationRecord(),
        invisibility_uptime_record=_InvisibilityUptimeRecord(),
    )


def test_current_direct_specialized_routes_are_explicit() -> None:
    for key in (
        "actual_heal", "critical_heal", "damage_shield", "bash_damage",
        "movement_speed", "sprint_speed", "stealthed_movement_speed",
        "detection_radius_reduction", "invisibility_duration",
    ):
        assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)


def test_duration_input_route_is_explicit() -> None:
    assert ExtremeSpecializedExecutionService.can_execute_with_duration_input("invisibility_uptime")
    assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("invisibility_uptime")
    assert tuple(
        row.key for row in ExtremeSpecializedExecutionService.requirements_for("invisibility_uptime")
    ) == ("duration_seconds",)


def test_saved_build_direct_routes_are_explicit() -> None:
    for key in ("actual_heal", "critical_heal", "damage_shield", "bash_damage"):
        assert ExtremeSpecializedExecutionService.requires_saved_build(key)
    for key in (
        "movement_speed", "sprint_speed", "stealthed_movement_speed",
        "detection_radius_reduction", "invisibility_duration", "invisibility_uptime",
    ):
        assert not ExtremeSpecializedExecutionService.requires_saved_build(key)


def test_single_event_records_no_longer_share_identical_input_requirements() -> None:
    assert ExtremeSpecializedExecutionService.requirements_for("bash_damage") == ()
    assert ExtremeSpecializedExecutionService.requirements_for("damage_shield") == ()


def test_resource_timeline_records_still_require_real_timeline_evidence() -> None:
    sustain = ExtremeSpecializedExecutionService.requirements_for("resource_sustain")
    ultimate = ExtremeSpecializedExecutionService.requirements_for("ultimate_generation")
    assert sustain == ultimate
    assert tuple(row.key for row in sustain) == ("duration_seconds", "timeline_evidence")


def test_saved_build_direct_execution_rejects_missing_build() -> None:
    for key in ("actual_heal", "damage_shield", "bash_damage"):
        with pytest.raises(ValueError, match="requires a saved-build starting context"):
            _service().execute(None, key)


def test_damage_shield_execution_normalizes_saved_build_lower_bound() -> None:
    result = _service().execute(SimpleNamespace(), "damage_shield", active_bar="back")
    assert result.value == pytest.approx(15000.0)
    assert result.value_text == "15,000"
    assert ("Shield skill", "Hardened Ward") in result.summary_rows
    assert ("Entity", "hardened_ward") in result.summary_rows
    assert result.global_maximum_proven is False


def test_bash_execution_normalizes_saved_build_lower_bound() -> None:
    result = _service().execute(SimpleNamespace(), "bash_damage", active_bar="back")
    assert result.value == pytest.approx(12345.0)
    assert result.value_text == "12,345"


def test_movement_execution_normalizes_reviewed_lower_bound_without_saved_build() -> None:
    result = _service().execute(None, "movement_speed")
    assert result.value_text == "141.0%"


def test_stealth_execution_normalizes_legal_gear_lower_bound_without_saved_build() -> None:
    result = _service().execute(None, "detection_radius_reduction")
    assert result.value_text == "2 m reviewed gear reduction"


def test_invisibility_duration_execution_normalizes_reviewed_provider_lower_bound() -> None:
    result = _service().execute(None, "invisibility_duration")
    assert result.value == pytest.approx(10.0)
    assert result.value_text == "10s reviewed lower bound"
    assert ("Reviewed provider", "Prowler's Talisman") in result.summary_rows
    assert ("Reviewed contiguous duration", "10s") in result.summary_rows
    assert result.global_maximum_proven is False
    assert result.unresolved == ("Invisibility provider corpus is not yet exhaustive",)


def test_invisibility_uptime_requires_duration_and_normalizes_reviewed_schedule() -> None:
    with pytest.raises(ValueError, match="requires family-specific scenario inputs"):
        _service().execute(None, "invisibility_uptime")

    result = _service().execute(None, "invisibility_uptime", duration_seconds=100.0)
    assert result.value == pytest.approx(0.30)
    assert result.value_text == "30.0% reviewed lower bound"
    assert ("Comparison horizon", "100s") in result.summary_rows
    assert ("Reviewed covered time", "30s") in result.summary_rows
    assert ("Reviewed windows", "3") in result.summary_rows
    assert ("Reviewed provider", "Prowler's Talisman") in result.summary_rows
    assert result.global_maximum_proven is False
