from pathlib import Path


def test_build_editor_save_and_cancel_are_distinct_semantic_actions() -> None:
    source = Path("ui/build_context_variant_support.py").read_text(encoding="utf-8")

    assert 'FoundryButton("Save This Build", role=ButtonRole.SUCCESS, compact=False)' in source
    assert 'FoundryButton("Cancel", role=ButtonRole.DANGER, compact=False)' in source
    assert "self.save_build_button = save" in source
    assert "self.cancel_build_button = cancel" in source
