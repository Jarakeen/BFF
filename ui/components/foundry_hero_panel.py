# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_hero_panel.py
#
# Purpose:
# Generic portrait/identity/facts detail panel.
#
# Covers both a boss detail block (portrait, name,
# title, facts, description) and a player Assignment
# Details panel (portrait, name, role, CP, sections) --
# same shape of data, same component.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.theme.fonts import Fonts
from ui.theme.metrics import Metrics


class FoundryHeroPanel(QWidget):
    """
    A portrait beside an identity block, with a row of
    key facts and optional freeform sections below.

        FoundryHeroPanel(
            name="Z'Maja",
            subtitle="Twilight Matriarch",
            description="An ancient shade of twilight and terror.",
            facts=[("Role", "Ranged DPS Boss"), ("Enrage", "10:00")],
            portrait=QPixmap("boss.png"),  # optional
        )

    `sections` is an optional list of (heading, [lines])
    tuples rendered below the facts, for things like
    "Phase Breakdown".
    """

    def __init__(
        self,
        name: str,
        subtitle: str = "",
        description: str = "",
        facts: list[tuple[str, str]] | None = None,
        portrait: QPixmap | None = None,
        sections: list[tuple[str, list[str]]] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryHeroPanel",
            True,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(12)

        top = QHBoxLayout()

        top.setSpacing(14)

        #
        # Portrait
        #

        self.portrait_label = QLabel()

        self.portrait_label.setProperty(
            "heroPortrait",
            True,
        )

        self.portrait_label.setFixedSize(90, 90)

        self.portrait_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.set_portrait(portrait)

        top.addWidget(self.portrait_label)

        #
        # Identity + facts
        #

        identity = QVBoxLayout()

        identity.setSpacing(4)

        self.name_label = QLabel(name)

        self.name_label.setProperty(
            "heroName",
            True,
        )

        self.name_label.setFont(
            Fonts.page_title()
        )

        identity.addWidget(self.name_label)

        if subtitle:

            self.subtitle_label = QLabel(subtitle)

            self.subtitle_label.setProperty(
                "heroSubtitle",
                True,
            )

            self.subtitle_label.setFont(
                Fonts.subtitle()
            )

            identity.addWidget(self.subtitle_label)

        if description:

            desc = QLabel(description)

            desc.setWordWrap(True)

            desc.setFont(Fonts.body())

            identity.addWidget(desc)

        identity.addStretch()

        top.addLayout(identity, 1)

        root.addLayout(top)

        #
        # Facts grid
        #

        if facts:

            grid = QGridLayout()

            grid.setHorizontalSpacing(20)

            grid.setVerticalSpacing(4)

            for i, (label, value) in enumerate(facts):

                row, col = divmod(i, 2)

                fact_label = QLabel(
                    label.upper()
                )

                fact_label.setProperty(
                    "heroFactLabel",
                    True,
                )

                fact_value = QLabel(value)

                fact_value.setProperty(
                    "heroFactValue",
                    True,
                )

                pair = QVBoxLayout()

                pair.setSpacing(0)

                pair.addWidget(fact_label)

                pair.addWidget(fact_value)

                grid.addLayout(pair, row, col)

            root.addLayout(grid)

        #
        # Sections
        #

        for heading, lines in (sections or []):

            heading_label = QLabel(
                heading.upper()
            )

            heading_label.setProperty(
                "heroFactLabel",
                True,
            )

            root.addWidget(heading_label)

            for line in lines:

                line_label = QLabel(f"• {line}")

                line_label.setWordWrap(True)

                line_label.setFont(Fonts.body())

                root.addWidget(line_label)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_portrait(
        self,
        portrait: QPixmap | None,
    ):

        if portrait is not None and not portrait.isNull():

            self.portrait_label.setPixmap(
                portrait.scaled(
                    self.portrait_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        else:

            self.portrait_label.setText("—")
