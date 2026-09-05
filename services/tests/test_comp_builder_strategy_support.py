from pathlib import Path


def test_strategy_action_uses_same_authoritative_bulk_optimizer() -> None:
    source = Path("ui/comp_builder_strategy_support.py").read_text(encoding="utf-8")

    assert '"Find Interesting Strategy"' in source
    assert "candidate_support._apply_best_candidates_to_all(page)" in source
    assert "CompCompositionStyle.OFF_META" in source
    assert "evaluate_provider_redistribution_strategy" in source
    assert "_ORIGINAL_OPTIMIZER(" in source


def test_strategy_support_uses_only_canonical_provider_ids_and_keeps_hard_solver_inputs() -> None:
    source = Path("ui/comp_builder_strategy_support.py").read_text(encoding="utf-8")

    assert "provider_ids_by_candidate=provider_ids_by_candidate" in source
    assert "novelty_by_candidate=novelty" in source
    assert "**kwargs" in source
    assert "strategy_score" not in source


def test_strategy_engine_remains_installed_but_button_is_hidden_from_main_workflow() -> None:
    support = Path("ui/comp_builder_strategy_support.py").read_text(encoding="utf-8")
    controls = Path("ui/comp_builder_main_controls_support.py").read_text(encoding="utf-8")
    layout = Path("ui/comp_builder_layout_support.py").read_text(encoding="utf-8")
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(encoding="utf-8")

    assert 'setProperty("compInterestingStrategy", True)' in support
    assert 'button = getattr(page, "comp_interesting_strategy_button", None)' in controls
    assert "button.hide()" in controls
    assert 'label.property("compInterestingStrategyHelp")' in controls
    assert "right.addWidget(actions, 0)" in layout
    assert "actions.setMinimumHeight(270)" in layout
    assert "actions.setMaximumHeight(310)" in layout
    assert "details.setMinimumHeight(700)" in layout
    assert "install_comp_builder_strategy()" in installer
