from pathlib import Path

from ui import build_context_variant_support
from ui import build_editor_lifecycle_support
from ui import phase5_potion_picker_support
from ui import scribing_simulator_support
from ui import scribing_support


def _source(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def test_lifecycle_support_owns_single_init_load_and_model_wrapper() -> None:
    source = _source(build_editor_lifecycle_support)

    assert "BuildEditor.__init__ = init_composed" in source
    assert "BuildEditor.load = load_composed" in source
    assert "BuildEditor.model = property(model_composed)" in source
    assert "_POST_INIT_HOOKS" in source
    assert "_PRE_LOAD_HOOKS" in source
    assert "_POST_LOAD_HOOKS" in source
    assert "_MODEL_POST_HOOKS" in source


def test_core_scribing_uses_pre_load_and_model_hooks() -> None:
    source = _source(scribing_support)

    assert 'register_pre_load("scribing.recipes", load_recipes)' in source
    assert 'register_model_post("scribing.recipes", store_recipes)' in source
    assert "BuildEditor.load =" not in source
    assert "BuildEditor.model =" not in source


def test_scribing_simulator_uses_post_load_hook_instead_of_wrapping_load() -> None:
    source = _source(scribing_simulator_support)

    assert 'register_post_load("scribing_simulator", refresh_after_load)' in source
    assert "BuildEditor.load =" not in source


def test_potion_support_uses_lifecycle_hooks_instead_of_wrapping_init_load_and_model() -> None:
    source = _source(phase5_potion_picker_support)

    assert 'register_post_init("searchable_build_dropdowns", _configure_all_build_dropdowns)' in source
    assert 'register_post_load("canonical_potion", load_canonical_potion)' in source
    assert 'register_model_post("canonical_potion", persist_canonical_potion)' in source
    assert "BuildEditor.__init__ =" not in source
    assert "BuildEditor.load =" not in source
    assert "BuildEditor.model =" not in source


def test_context_variants_use_post_load_and_model_hooks() -> None:
    source = _source(build_context_variant_support)

    assert 'register_post_load("context_variants", load_context_variants)' in source
    assert 'register_model_post("context_variants", store_context_variants)' in source
    assert "BuildEditor.load =" not in source
    assert "BuildEditor.model =" not in source
