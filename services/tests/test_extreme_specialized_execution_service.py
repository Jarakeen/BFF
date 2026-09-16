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


def test_heal_event_records_are_direct_specialized_routes() -> None:
    assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("actual_heal")
    assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("critical_heal")
    assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("bash_damage")


def test_family_requirements_are_shared_by_related_records() -> None:
    bash = ExtremeSpecializedExecutionService.requirements_for("bash_damage")
    shield = ExtremeSpecializedExecutionService.requirements_for("damage_shield")
    assert bash == shield
    assert tuple(row.key for row in bash) == ("event_source",)

    sustain = ExtremeSpecializedExecutionService.requirements_for("resource_sustain")
    ultimate = ExtremeSpecializedExecutionService.requirements_for("ultimate_generation")
    assert sustain == ultimate
    assert tuple(row.key for row in sustain) == ("duration_seconds", "timeline_evidence")

    movement = ExtremeSpecializedExecutionService.requirements_for("movement_speed")
    sprint = ExtremeSpecializedExecutionService.requirements_for("sprint_speed")
    stealth_move = ExtremeSpecializedExecutionService.requirements_for("stealthed_movement_speed")
    assert movement == sprint == stealth_move
    assert tuple(row.key for row in movement) == ("movement_sources",)

    invis_duration = ExtremeSpecializedExecutionService.requirements_for("invisibility_duration")
    invis_uptime = ExtremeSpecializedExecutionService.requirements_for("invisibility_uptime")
    assert invis_duration == invis_uptime
    assert tuple(row.key for row in invis_duration) == ("duration_seconds", "invisibility_windows")


def test_heal_event_execution_normalizes_family_result_for_ui() -> None:
    service = ExtremeSpecializedExecutionService(healing_events=_HealingEvents())

    result = service.execute(
        SimpleNamespace(),
        "actual_heal",
        active_bar="back",
    )

    assert result.objective_key == "actual_heal"
    assert result.execution_family == "actual-heal-event"
    assert result.value == pytest.approx(54321.0)
    assert result.mechanic_complete is False
    assert result.global_maximum_proven is False
    assert ("Heal", "Fixture Heal") in result.summary_rows
    assert ("Class", "Warden") in result.summary_rows
    assert ("Bar slot", "3") in result.summary_rows
    assert result.unresolved == ("fixture unresolved",)
    assert result.search_scope == ("shared H1 search",)
    assert result.omitted_scope == ("fixture omitted",)


def test_specialized_family_needing_inputs_names_shared_requirements() -> None:
    service = ExtremeSpecializedExecutionService(healing_events=_HealingEvents())

    with pytest.raises(
        ValueError,
        match="requires family-specific scenario inputs before execution: Movement Sources",
    ):
        service.execute(SimpleNamespace(), "movement_speed")
