from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from services.help_topics import HELP_TOPICS, HelpTopic, help_topic, search_help_topics
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class HelpPage(FoundryPage):
    """Searchable, data-driven application help center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._populate_topics()
        self.show_topic("getting_started")

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Help & Guide",
            subtitle="Find the page, concept, or workflow you need without excavating a manual.",
            department="FIELD OFFICE • HELP",
        )
        self.set_header(self.header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search help: builds, sustain, raid times, mechanics, exports...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._populate_topics)
        self.header.add_context_widget(self._context_field("SEARCH HELP", self.search))

        workspace = QWidget()
        root = QHBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        index = FoundryCard("Help Topics", "?").set_watermark("compass", 0.04)
        self.topic_list = QListWidget()
        self.topic_list.currentItemChanged.connect(self._topic_selected)
        index.addWidget(self.topic_list)
        root.addWidget(index, 1)

        article = FoundryCard("Guide", "✎").set_watermark("feather", 0.06)
        article_scroll = QScrollArea()
        article_scroll.setWidgetResizable(True)
        article_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        article_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        article_host = QWidget()
        self.article_layout = QVBoxLayout(article_host)
        self.article_layout.setContentsMargins(4, 4, 4, 4)
        self.article_layout.setSpacing(8)

        self.article_title = QLabel("Help")
        self.article_title.setProperty("heroTitle", True)
        self.article_layout.addWidget(self.article_title)

        self.article_summary = QLabel()
        self.article_summary.setWordWrap(True)
        self.article_summary.setProperty("heroSubtitle", True)
        self.article_layout.addWidget(self.article_summary)

        self.section_host = QWidget()
        self.section_layout = QVBoxLayout(self.section_host)
        self.section_layout.setContentsMargins(0, 8, 0, 0)
        self.section_layout.setSpacing(8)
        self.article_layout.addWidget(self.section_host)

        related_card = FoundryCard("Related Topics", "↗").make_parchment()
        self.related_label = QLabel()
        self.related_label.setWordWrap(True)
        related_card.addWidget(self.related_label)
        self.article_layout.addWidget(related_card)
        self.article_layout.addStretch(1)

        article_scroll.setWidget(article_host)
        article.addWidget(article_scroll)
        root.addWidget(article, 3)

        self.add_workspace(workspace)
        self.status = FoundryStatusBar()
        self.set_status(self.status)
        self.status.info(f"Help ready • {len(HELP_TOPICS)} topic(s).")

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _populate_topics(self, *_args) -> None:
        query = self.search.text() if hasattr(self, "search") else ""
        current_key = ""
        current = self.topic_list.currentItem() if hasattr(self, "topic_list") else None
        if current is not None:
            current_key = str(current.data(Qt.ItemDataRole.UserRole) or "")

        topics = search_help_topics(query)
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        for topic in topics:
            item = QListWidgetItem(topic.title)
            item.setData(Qt.ItemDataRole.UserRole, topic.key)
            self.topic_list.addItem(item)
        self.topic_list.blockSignals(False)

        preferred = current_key or "getting_started"
        for row in range(self.topic_list.count()):
            item = self.topic_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == preferred:
                self.topic_list.setCurrentRow(row)
                return
        if self.topic_list.count():
            self.topic_list.setCurrentRow(0)
        else:
            self._render_no_results(query)

    def _topic_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        key = str(current.data(Qt.ItemDataRole.UserRole) or "")
        self.show_topic(key)

    def show_topic(self, key: str) -> None:
        topic = help_topic(key)
        if topic is None:
            return
        self._render_topic(topic)
        for row in range(self.topic_list.count()):
            item = self.topic_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == topic.key:
                if self.topic_list.currentRow() != row:
                    self.topic_list.setCurrentRow(row)
                break

    def _clear_sections(self) -> None:
        while self.section_layout.count():
            item = self.section_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_topic(self, topic: HelpTopic) -> None:
        self.article_title.setText(topic.title)
        self.article_summary.setText(topic.summary)
        self._clear_sections()

        for section in topic.sections:
            card = FoundryCard(section.title, "•")
            body = QLabel(section.body)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            card.addWidget(body)
            self.section_layout.addWidget(card)

        related_titles = [
            related.title
            for key in topic.related
            if (related := help_topic(key)) is not None
        ]
        self.related_label.setText(" • ".join(related_titles) if related_titles else "No related topics.")
        self.status.success(f"Showing help for {topic.title}.")

    def _render_no_results(self, query: str) -> None:
        self.article_title.setText("No matching help topic")
        self.article_summary.setText(
            f"Nothing matched {query!r}. Try a page name, feature, mechanic term, or workflow keyword."
        )
        self._clear_sections()
        self.related_label.setText("")
        self.status.warning("No help topics matched the current search.")
