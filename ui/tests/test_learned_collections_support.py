from pathlib import Path

from ui import collectibles_learned_recipe_support
from services import learned_recipe_service


def test_collectibles_support_exposes_recipes_and_furnishing_plans() -> None:
    source = Path(collectibles_learned_recipe_support.__file__).read_text(encoding="utf-8")

    assert '("Furnishing Plans", "collectibles:Furnishing Plans")' in source
    assert '("Recipes", "collectibles:Recipes")' in source
    assert 'self.collected.setText("Learned")' in source
    assert 'service.set_learned_batch' in source


def test_learned_recipe_categories_are_canonical() -> None:
    assert learned_recipe_service.KIND_BY_CATEGORY == {
        "Recipes": "provisioning_recipe",
        "Furnishing Plans": "furnishing_plan",
    }
