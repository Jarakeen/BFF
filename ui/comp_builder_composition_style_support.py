from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel

from services.comp_builder_composition_style import (
    CompCompositionStyle,
    composition_style_options,
    composition_style_policy,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _actions_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Actions":
            return card
    return None


def selected_composition_style(page) -> CompCompositionStyle:
    combo = getattr(page, "comp_composition_style_combo", None)
    if combo is None:
        return CompCompositionStyle.PROVEN
    value = combo.currentData()
    try:
        return CompCompositionStyle(str(value))
    except ValueError:
        return CompCompositionStyle.PROVEN


def _update_style_help(page) -> None:
    style = selected_composition_style(page)
    policy = composition_style_policy(style)
    label = getattr(page, "comp_composition_style_help", None)
    if label is not None:
        label.setText(policy.description)
    page._comp_composition_style = style


def _install_style_ui(page) -> None:
    card = _actions_card(page)
    if card is None:
        return

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    title = QLabel("COMPOSITION STYLE")
    title.setProperty("sidebarHeading", True)
    row.addWidget(title)

    combo = QComboBox()
    for policy in composition_style_options():
        combo.addItem(policy.label, policy.style.value)
    combo.setCurrentIndex(0)
    combo.setMinimumWidth(190)
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setProperty("compCompositionStyle", True)
    row.addWidget(combo, 1)
    card.body_layout.insertLayout(1, row)

    help_label = QLabel()
    help_label.setWordWrap(True)
    help_label.setProperty("muted", True)
    help_label.setProperty("compCompositionStyleHelp", True)
    card.body_layout.insertWidget(2, help_label)

    page.comp_composition_style_combo = combo
    page.comp_composition_style_help = help_label
    page._comp_composition_style = CompCompositionStyle.PROVEN
    combo.currentIndexChanged.connect(lambda *_args: _update_style_help(page))
    _update_style_help(page)


def _comp_init_with_composition_style(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_style_ui(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_composition_style
    CompBuilderPage._selected_composition_style = selected_composition_style
    _INSTALLED = True
