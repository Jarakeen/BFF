from __future__ import annotations

from PySide6.QtWidgets import QLabel

from services.comp_builder_composition_style import CompCompositionStyle
from services.comp_builder_strategy_evidence import evaluate_provider_redistribution_strategy
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_OPTIMIZER = None


def _actions_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Actions":
            return card
    return None


def _optimizer_with_strategy_evidence(*, pools, provider_ids_by_candidate=None, novelty_by_candidate=None, composition_style=CompCompositionStyle.PROVEN, **kwargs):
    assert _ORIGINAL_OPTIMIZER is not None
    provider_ids_by_candidate = dict(provider_ids_by_candidate or {})
    novelty = dict(novelty_by_candidate or {})

    candidates = tuple(
        candidate
        for pool in pools
        for candidate in pool.candidates
    )
    strategy = evaluate_provider_redistribution_strategy(
        candidates,
        provider_ids_by_candidate=provider_ids_by_candidate,
    )
    for candidate_id, score in strategy.score_by_candidate.items():
        novelty[candidate_id] = novelty.get(candidate_id, 0.0) + score

    return _ORIGINAL_OPTIMIZER(
        pools=pools,
        provider_ids_by_candidate=provider_ids_by_candidate,
        novelty_by_candidate=novelty,
        composition_style=composition_style,
        **kwargs,
    )


def _run_interesting_strategy(page) -> None:
    from ui import comp_builder_build_candidate_support as candidate_support

    combo = getattr(page, "comp_composition_style_combo", None)
    if combo is not None:
        index = combo.findData(CompCompositionStyle.OFF_META.value)
        if index >= 0:
            combo.setCurrentIndex(index)
    page._comp_composition_style = CompCompositionStyle.OFF_META
    candidate_support._apply_best_candidates_to_all(page)


def _install_button(page) -> None:
    card = _actions_card(page)
    if card is None:
        return

    page.comp_interesting_strategy_button = FoundryButton(
        "Find Interesting Strategy",
        role=ButtonRole.SUCCESS,
        compact=True,
    )
    page.comp_interesting_strategy_button.setProperty("compInterestingStrategy", True)
    page.comp_interesting_strategy_button.clicked.connect(
        lambda *_args: _run_interesting_strategy(page)
    )
    card.body_layout.insertWidget(3, page.comp_interesting_strategy_button)

    note = QLabel(
        "Strategy discovery rewards unusual canonically proven provider ownership only after raid legality is satisfied."
    )
    note.setWordWrap(True)
    note.setProperty("muted", True)
    note.setProperty("compInterestingStrategyHelp", True)
    card.body_layout.insertWidget(4, note)


def install() -> None:
    global _INSTALLED, _ORIGINAL_OPTIMIZER
    if _INSTALLED:
        return

    from ui import comp_builder_team_candidate_optimizer_support as optimizer_support
    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_OPTIMIZER = optimizer_support.optimize_comp_team_candidates
    optimizer_support.optimize_comp_team_candidates = _optimizer_with_strategy_evidence

    original_init = CompBuilderPage.__init__

    def init_with_strategy_action(self, parent=None):
        original_init(self, parent)
        _install_button(self)

    CompBuilderPage.__init__ = init_with_strategy_action
    _INSTALLED = True
