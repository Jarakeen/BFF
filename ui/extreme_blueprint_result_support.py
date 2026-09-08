from __future__ import annotations

from engine.config import get_data_dir
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_consumable_result_support import (
    extreme_food_winners,
    format_extreme_food_result,
)

_INSTALLED = False


def _reviewed_mastery_row(notes: tuple[str, ...]) -> tuple[str, str] | None:
    prefix = "Best currently reviewed pure-class mastery route for "
    for note in notes:
        text = str(note or "").strip()
        if not text.startswith(prefix) or ": " not in text:
            continue
        route = text.split(": ", 1)[1]
        route = route.split("; projected mastery-only delta", 1)[0].strip()
        if route:
            return "Class Mastery (reviewed)", route
    return None


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.extreme_optimization_page import ExtremeOptimizationPage

    original_rows = ExtremeOptimizationPage._blueprint_rows
    provisioning = ProvisioningStaticRepository(get_data_dir() / "eso.db")

    def blueprint_rows_with_result_evidence(result):
        rows = list(original_rows(result))

        mastery_row = _reviewed_mastery_row(tuple(result.notes))
        if mastery_row is not None:
            class_index = next(
                (index for index, (label, _value) in enumerate(rows) if label == "Class"),
                0,
            )
            rows.insert(class_index + 1, mastery_row)

        food = extreme_food_winners(
            result.objective.key,
            selected_food=str(result.build.Food or ""),
            repository=provisioning,
        )
        food_text, co_winners = format_extreme_food_result(food)
        food_index = next(
            (index for index, (label, _value) in enumerate(rows) if label == "Food"),
            None,
        )
        if food_index is not None:
            rows[food_index] = ("Food", food_text)
            if co_winners:
                rows.insert(food_index + 1, ("Food co-winners", co_winners))

        return tuple(rows)

    ExtremeOptimizationPage._blueprint_rows = staticmethod(blueprint_rows_with_result_evidence)
    _INSTALLED = True
