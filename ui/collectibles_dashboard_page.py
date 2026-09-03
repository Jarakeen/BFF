# ==================================================
# Black Feather Foundry
# ui/collectibles_dashboard_page.py
# Fantasy-flavored overview for collectible completion.
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.eso_collectible_database_service import SIDEBAR_CATEGORIES
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar


_CATEGORY_FLAVOR = {
    "Mounts": ("Stable Ledger", "Hooves, paws, claws, and several transportation decisions of questionable legality."),
    "Pets": ("Menagerie", "Tiny companions acquired through heroism, commerce, and an alarming lack of impulse control."),
    "Allies / Assistants": ("Retinue", "People who follow you around because apparently adventuring alone was too peaceful."),
    "Houses": ("Estates", "A completely reasonable number of properties for one wandering adventurer."),
    "Costumes": ("Wardrobe", "Battle-ready attire, ceremonial finery, and clothes nobody packed sensibly."),
    "Skins": ("Arcane Visages", "Evidence that 'looking normal' was never a serious design constraint."),
    "Polymorphs": ("Borrowed Shapes", "Become something else for a while. Paperwork remains unchanged."),
    "Personalities": ("Mannerisms", "Because standing normally is apparently beneath us."),
    "Hairstyles & Adornments": ("Vanity Cabinet", "Hair, markings, jewelry, and the eternal war against visual restraint."),
    "Mementos": ("Curio Shelf", "Magical souvenirs with no practical reason to be this satisfying."),
    "Emotes": ("Gesture Grimoire", "A scholarly archive of waving, dancing, pointing, and other critical battlefield functions."),
    "Customized Actions": ("Ritual Flourishes", "Ordinary actions, now with significantly more theater."),
    "Weapon Styles": ("Armory Display", "The enemy was already defeated. Looking good was the follow-up mechanic."),
    "Armor Styles": ("Outfit Archive", "For when defeating Tamriel is not enough and the silhouette must also be correct."),
    "Furnishings": ("Vault of Things", "Objects acquired for houses that were acquired to hold the objects. Elegant system."),
    "Fragments": ("Relic Fragments", "Several small things patiently waiting to become one larger thing."),
    "Tools & Upgrades": ("Oddments & Upgrades", "Useful account curiosities that refused to fit politely anywhere else."),
}


def _percent(owned: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, round((owned / total) * 100)))


def _progress_epithet(percent: int, total: int) -> str:
    if total <= 0:
        return "No catalog entries yet"
    if percent >= 100:
        return "Archive complete. Suspiciously competent."
    if percent >= 80:
        return "Nearly legendary"
    if percent >= 60:
        return "A formidable hoard"
    if percent >= 40:
        return "The vault is filling"
    if percent >= 20:
        return "A respectable beginning"
    if percent > 0:
        return "The first relics are secured"
    return "Unexplored territory"


class CollectiblesDashboardPage(QWidget):
    """Main Collections landing page summarizing every sidebar category."""

    categoryRequested = Signal(str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._category_widgets: dict[str, tuple[FoundryCard, QProgressBar, QLabel, QLabel]] = {}
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Collectibles",
            subtitle="A field ledger of everything acquired, adopted, unlocked, worn, summoned, displayed, or otherwise dragged home.",
            department="Collections",
        )

        self.overall_card = FoundryCard("Collection Chronicle")
        self.overall_card.set_watermark("feather", 0.10)
        self.overall_count = QLabel("0 / 0 secured")
        self.overall_count.setProperty("collectibleDashboardHero", True)
        self.overall_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setMinimumHeight(28)
        self.overall_progress.setProperty("collectibleDashboardProgress", True)
        self.overall_epithet = QLabel("Consulting the vault ledgers...")
        self.overall_epithet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overall_epithet.setProperty("muted", True)
        self.overall_card.addWidget(self.overall_count)
        self.overall_card.addWidget(self.overall_progress)
        self.overall_card.addWidget(self.overall_epithet)

        intro = QLabel(
            "Each ledger below reflects saved ownership progress. Open one to inspect the collection, mark finds, "
            "or discover exactly how many mounts Tamriel expects one person to store somewhere."
        )
        intro.setWordWrap(True)
        intro.setProperty("muted", True)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        for index, (category, _sort_order) in enumerate(SIDEBAR_CATEGORIES):
            card = self._build_category_card(category)
            self.grid.addWidget(card, index // 2, index % 2)

        self.status = FoundryStatusBar()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(self.header)
        layout.addWidget(self.overall_card)
        layout.addWidget(intro)
        layout.addLayout(self.grid)
        layout.addWidget(self.status)

    def _build_category_card(self, category: str) -> FoundryCard:
        title, flavor = _CATEGORY_FLAVOR.get(category, (category, "Collection progress."))
        card = FoundryCard(title)
        card.set_watermark("compass", 0.06)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        category_name = QLabel(category)
        category_name.setProperty("collectibleDashboardCategory", True)
        category_name.setWordWrap(True)

        flavor_label = QLabel(flavor)
        flavor_label.setWordWrap(True)
        flavor_label.setProperty("muted", True)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setTextVisible(True)
        progress.setMinimumHeight(22)
        progress.setProperty("collectibleDashboardProgress", True)

        count_label = QLabel("0 / 0 collected")
        count_label.setProperty("collectibleDashboardCount", True)
        state_label = QLabel("Unexplored territory")
        state_label.setProperty("muted", True)

        footer = QHBoxLayout()
        footer.addWidget(count_label)
        footer.addStretch(1)
        footer.addWidget(state_label)

        open_button = QPushButton(f"Open {category}")
        open_button.setProperty("primary", True)
        open_button.clicked.connect(
            lambda checked=False, value=category: self.categoryRequested.emit(value)
        )

        card.addWidget(category_name)
        card.addWidget(flavor_label)
        card.addWidget(progress)
        card.addLayout(footer)
        card.addWidget(open_button)

        self._category_widgets[category] = (card, progress, count_label, state_label)
        return card

    def refresh(self) -> None:
        if not self.service.available:
            self.overall_progress.setValue(0)
            self.overall_progress.setFormat("Catalog unavailable")
            self.overall_count.setText("Collection ledger unavailable")
            self.overall_epithet.setText(self.service.bootstrap_message or "Collectible reference data is unavailable.")
            for category, (_card, progress, count_label, state_label) in self._category_widgets.items():
                progress.setValue(0)
                progress.setFormat("Unavailable")
                count_label.setText("0 / 0 collected")
                state_label.setText("Ledger unavailable")
            self.status.warning(self.service.bootstrap_message or "Collectible reference data is unavailable.")
            return

        owned_total = 0
        catalog_total = 0
        populated_categories = 0

        for category, (_card, progress, count_label, state_label) in self._category_widgets.items():
            owned, total = self.service.progress_summary(category)
            percent = _percent(owned, total)
            progress.setValue(percent)
            progress.setFormat(f"{percent}%")
            count_label.setText(f"{owned:,} / {total:,} collected")
            state_label.setText(_progress_epithet(percent, total))
            owned_total += owned
            catalog_total += total
            if total:
                populated_categories += 1

        overall_percent = _percent(owned_total, catalog_total)
        self.overall_progress.setValue(overall_percent)
        self.overall_progress.setFormat(f"{overall_percent}% complete")
        self.overall_count.setText(f"{owned_total:,} / {catalog_total:,} collectibles secured")
        self.overall_epithet.setText(_progress_epithet(overall_percent, catalog_total))
        self.overall_card.set_badge(f"{overall_percent}%")
        self.status.info(
            f"{populated_categories} collection ledgers · {owned_total:,}/{catalog_total:,} total collectibles secured."
        )
