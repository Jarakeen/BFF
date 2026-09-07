from pathlib import Path

from services.comp_builder_composition_style import (
    CompCompositionStyle,
    composition_style_options,
    composition_style_policy,
)


def test_composition_style_options_cover_proven_through_off_meta() -> None:
    assert [policy.style for policy in composition_style_options()] == [
        CompCompositionStyle.PROVEN,
        CompCompositionStyle.PERFORMANCE,
        CompCompositionStyle.EXPERIMENTAL,
        CompCompositionStyle.OFF_META,
    ]


def test_off_meta_policy_values_novelty_without_removing_relevance() -> None:
    policy = composition_style_policy(CompCompositionStyle.OFF_META)

    assert policy.novelty_weight > 0
    assert policy.relevance_weight > 0
    assert "required providers" in policy.description


def test_comp_maker_style_selector_keeps_policy_state_but_moves_to_header() -> None:
    style_source = Path("ui/comp_builder_composition_style_support.py").read_text(encoding="utf-8")
    controls = Path("ui/comp_builder_main_controls_support.py").read_text(encoding="utf-8")

    assert '"COMPOSITION STYLE"' in style_source
    assert 'card.title_label.text().strip() == "Actions"' in style_source
    assert "page._comp_composition_style = style" in style_source
    assert "help_label.setWordWrap(True)" in style_source
    assert 'page.header.add_context_widget(page._context_field("PLAN STYLE", style_combo))' in controls
    assert 'label.property("compCompositionStyleHelp")' in controls


def test_whole_team_optimizer_receives_selected_style_and_observed_novelty() -> None:
    source = Path("ui/comp_builder_team_candidate_optimizer_support.py").read_text(
        encoding="utf-8"
    )

    assert "CompBuilderNoveltyEvidenceService" in source
    assert "novelty_service.evaluate_candidates" in source
    assert "page._comp_novelty_by_candidate = dict(novelty_by_candidate)" in source
    assert "composition_style=style" in source
    assert "novelty_by_candidate=novelty_by_candidate" in source


def test_rylo_theme_covers_composition_style_and_compact_actions_layout() -> None:
    rylo = Path("ui/comp_builder_rylo_support.py").read_text(encoding="utf-8")
    layout = Path("ui/comp_builder_layout_support.py").read_text(encoding="utf-8")
    controls = Path("ui/comp_builder_main_controls_support.py").read_text(encoding="utf-8")

    assert 'QComboBox[compCompositionStyle="true"]' in rylo
    assert 'QLabel[compCompositionStyleHelp="true"]' in rylo
    assert "right.addWidget(actions, 0)" in layout
    assert "actions.setMinimumHeight(" in layout
    assert "actions.setMaximumHeight(" in layout
    assert "ScrollBarAlwaysOff" in layout
    assert "columns.addLayout(right, 1)" in layout
    assert "actions.set_body_margins(8, 5, 8, 6)" in controls
    assert "actions.set_body_spacing(4)" in controls
