from __future__ import annotations

"""Community News page.

Combined ESO community news feed + trending discussion + local search, so the
player doesn't have to separately check ESO-Hub, Reddit, and the forums by hand.
"""

from datetime import datetime, timezone
from html import escape

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.community_feed_service import CommunityFeedService, FeedItem
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.raid_review_async_task import RaidReviewAsyncTask
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts

_MAX_ROWS_PER_TAB = 40


class CommunityNewsPage(FoundryPage):
    """What's new and what's trending in the ESO community, with local search."""

    def __init__(self, service: CommunityFeedService | None = None, parent=None):
        super().__init__(parent)
        self.service = service or CommunityFeedService()
        # None = not loaded yet (still "Loading..."); [] = loaded, genuinely empty.
        self._latest_items: list[FeedItem] | None = None
        self._trending_items: list[FeedItem] | None = None
        self._latest_task: RaidReviewAsyncTask | None = None
        self._trending_task: RaidReviewAsyncTask | None = None
        self.build_ui()
        self.connect_signals()
        self.refresh()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Community News",
            subtitle="What's new and what's trending across the ESO community, in one place.",
            department="COMMUNITY",
        )
        self.set_header(self.header)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search loaded news and posts...")
        self.search.setClearButtonEnabled(True)

        self.refresh_button = FoundryButton("Refresh", role=ButtonRole.SECONDARY, compact=True)

        controls.addWidget(self.search, 1)
        controls.addWidget(self.refresh_button)

        news_card = FoundryCard(title="Community News", icon="achievement")
        card_body = QWidget()
        card_layout = QVBoxLayout(card_body)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(8)
        card_layout.addLayout(controls)

        self.tabs = QTabWidget()
        self.latest_label = self._build_feed_label()
        self.trending_label = self._build_feed_label()
        self.tabs.addTab(self._scrollable(self.latest_label), "Latest")
        self.tabs.addTab(self._scrollable(self.trending_label), "Trending")
        card_layout.addWidget(self.tabs, 1)

        self.note = QLabel(
            "Latest merges ESO-Hub's news feed with r/elderscrollsonline's newest posts. "
            "Trending is Reddit's own hot ranking -- genuine community engagement, not an "
            "official ZOS signal. Search filters what's already loaded below; it doesn't "
            "query the sites directly."
        )
        self.note.setWordWrap(True)
        self.note.setFont(Fonts.small())
        self.note.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        card_layout.addWidget(self.note)

        news_card.addWidget(card_body)
        self.add_workspace(news_card)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    @staticmethod
    def _build_feed_label() -> QLabel:
        label = QLabel("Loading...")
        label.setWordWrap(True)
        label.setOpenExternalLinks(False)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        return label

    @staticmethod
    def _scrollable(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(widget)
        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh)
        self.search.textChanged.connect(self._on_search_changed)
        self.latest_label.linkActivated.connect(self._open_link)
        self.trending_label.linkActivated.connect(self._open_link)

    @staticmethod
    def _open_link(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def refresh(self) -> None:
        """Refresh both tabs. Each source loads on its own worker thread so a slow
        or failing source never blocks the other, and neither blocks the GUI."""
        self.status.info("Loading community news...")
        self.refresh_button.setEnabled(False)

        self._latest_task = RaidReviewAsyncTask(self.service.fetch_latest, self)
        self._latest_task.succeeded.connect(self._on_latest_loaded)
        self._latest_task.failed.connect(self._on_latest_failed)
        self._latest_task.finished.connect(self._on_task_finished)
        self._latest_task.start()

        self._trending_task = RaidReviewAsyncTask(self.service.fetch_trending, self)
        self._trending_task.succeeded.connect(self._on_trending_loaded)
        self._trending_task.failed.connect(self._on_trending_failed)
        self._trending_task.finished.connect(self._on_task_finished)
        self._trending_task.start()

    def _on_task_finished(self) -> None:
        latest_running = self._latest_task is not None and self._latest_task.isRunning()
        trending_running = self._trending_task is not None and self._trending_task.isRunning()
        if not latest_running and not trending_running:
            self.refresh_button.setEnabled(True)

    def _on_latest_loaded(self, items: object) -> None:
        self._latest_items = list(items) if isinstance(items, list) else []
        self._render(self.latest_label, self._latest_items, self.search.text())
        self.status.success(f"{len(self._latest_items)} news item(s) loaded.")

    def _on_latest_failed(self, message: str) -> None:
        self._latest_items = []
        self.latest_label.setText(f"Couldn't load news: {escape(message)}")
        self.status.error(f"News feed failed: {message}")

    def _on_trending_loaded(self, items: object) -> None:
        self._trending_items = list(items) if isinstance(items, list) else []
        self._render(self.trending_label, self._trending_items, self.search.text())

    def _on_trending_failed(self, message: str) -> None:
        self._trending_items = []
        self.trending_label.setText(f"Couldn't load trending posts: {escape(message)}")

    # --------------------------------------------------
    # Search / render
    # --------------------------------------------------

    def _on_search_changed(self, text: str) -> None:
        if self._latest_items is not None:
            self._render(self.latest_label, self._latest_items, text)
        if self._trending_items is not None:
            self._render(self.trending_label, self._trending_items, text)

    def _render(self, label: QLabel, items: list[FeedItem], search_text: str) -> None:
        query = search_text.strip().casefold()
        filtered = [item for item in items if not query or query in item.search_text]
        if not items:
            label.setText("No items loaded yet.")
            return
        if not filtered:
            label.setText("No loaded items match that search.")
            return
        label.setText("<br><br>".join(self._row_html(item) for item in filtered[:_MAX_ROWS_PER_TAB]))

    @staticmethod
    def _row_html(item: FeedItem) -> str:
        meta_bits = [item.source]
        if item.published_at is not None:
            meta_bits.append(_relative_time(item.published_at))
        if item.score is not None:
            meta_bits.append(f"{item.score} pts")
        if item.comment_count is not None:
            meta_bits.append(f"{item.comment_count} comments")
        meta = " &middot; ".join(escape(bit) for bit in meta_bits)

        title_html = f'<a href="{escape(item.url)}">{escape(item.title)}</a>'
        summary_html = ""
        if item.summary:
            trimmed = item.summary if len(item.summary) <= 180 else item.summary[:177] + "..."
            summary_html = f'<br><span style="color:{Colors.TEXT_MUTED};">{escape(trimmed)}</span>'

        return (
            f'<span style="font-size:10.5pt;">{title_html}</span><br>'
            f'<span style="color:{Colors.GOLD}; font-size:8.5pt;">{meta}</span>'
            f"{summary_html}"
        )


def _relative_time(when: datetime) -> str:
    now = datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    seconds = int((now - when).total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w ago"
    months = days // 30
    return f"{months}mo ago"


__all__ = ["CommunityNewsPage"]
