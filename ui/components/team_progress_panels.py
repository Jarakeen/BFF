from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from ui.components.foundry_card import FoundryCard


@dataclass(frozen=True)
class TeamCoverageItem:
    name: str
    provider: str = ""
    covered: bool = False


DISPLAY_COVERAGE_EFFECTS = (
    "Major Vulnerability",
    "Minor Vulnerability",
    "Major Courage",
    "Major Intellect",
    "Major Endurance",
    "Major Breach",
    "Minor Breach",
    "Off-Balance",
    "Major Slayer",
    "Crowd Control",
)


BUILD_COVERAGE_ALIASES = {
    "Major Vulnerability": ("major vulnerability", "colossus", "turning tide"),
    "Minor Vulnerability": ("minor vulnerability",),
    "Major Courage": ("major courage", "spell power cure", "olorime"),
    "Major Intellect": ("major intellect",),
    "Major Endurance": ("major endurance",),
    "Major Breach": ("major breach",),
    "Minor Breach": ("minor breach",),
    "Off-Balance": ("off-balance", "off balance"),
    "Major Slayer": ("major slayer", "pillager's profit", "roaring opportunist"),
    "Crowd Control": ("crowd control", "immobilize", "stun", "pull", "chains", "talons"),
}


def build_search_text(build) -> str:
    values: list[object] = []
    values.extend(getattr(build, "FrontBarSkills", ()) or ())
    values.extend(getattr(build, "BackBarSkills", ()) or ())
    for weapon_name in ("FrontBarWeapon", "BackBarWeapon"):
        weapon = getattr(build, weapon_name, None)
        if weapon is not None:
            values.append(getattr(weapon, "Set", ""))
    armor = getattr(build, "Armor", {}) or {}
    if isinstance(armor, dict):
        values.extend(
            entry.get("Set", "")
            for entry in armor.values()
            if isinstance(entry, dict)
        )
    values.extend(
        (
            getattr(build, "BuildName", ""),
            getattr(build, "Role", ""),
            getattr(build, "EsoClass", ""),
        )
    )
    return " ".join(str(value or "") for value in values).casefold()


def coverage_from_builds(builds) -> tuple[TeamCoverageItem, ...]:
    rows: list[TeamCoverageItem] = []
    build_rows = tuple(builds)
    for effect in DISPLAY_COVERAGE_EFFECTS:
        aliases = BUILD_COVERAGE_ALIASES.get(effect, (effect.casefold(),))
        providers: list[str] = []
        for build in build_rows:
            text = build_search_text(build)
            if not any(alias.casefold() in text for alias in aliases):
                continue
            provider = (
                str(getattr(build, "Name", "") or "").strip()
                or str(getattr(build, "Gamertag", "") or "").strip()
                or str(getattr(build, "BuildName", "") or "").strip()
                or "Saved build"
            )
            if provider not in providers:
                providers.append(provider)
        rows.append(
            TeamCoverageItem(
                name=effect,
                provider=", ".join(providers[:2]),
                covered=bool(providers),
            )
        )
    return tuple(rows)


def coverage_from_declared_text(rows: tuple[tuple[str, str], ...]) -> tuple[TeamCoverageItem, ...]:
    """Resolve only explicit composition declarations, never class-name guesses."""

    result: list[TeamCoverageItem] = []
    for effect in DISPLAY_COVERAGE_EFFECTS:
        aliases = BUILD_COVERAGE_ALIASES.get(effect, (effect.casefold(),))
        providers: list[str] = []
        for slot_name, text in rows:
            lowered = str(text or "").casefold()
            if any(alias.casefold() in lowered for alias in aliases):
                providers.append(slot_name)
        result.append(
            TeamCoverageItem(
                name=effect,
                provider=", ".join(providers[:2]),
                covered=bool(providers),
            )
        )
    return tuple(result)


class TeamCoverageGrid(QWidget):
    """Shared before/after coverage scoreboard used by Comp Builder and Optimization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(8)
        self._layout.setVerticalSpacing(8)
        self._labels: list[QLabel] = []

    def set_items(self, items: tuple[TeamCoverageItem, ...]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._labels.clear()

        for index, item in enumerate(items):
            tile = QWidget()
            tile.setProperty("coverageTile", True)
            layout = QVBoxLayout(tile)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(3)

            title = QLabel(item.name)
            title.setProperty("sidebarHeading", True)
            state = QLabel(
                f"{'✓' if item.covered else '○'}  {item.provider or 'Not covered yet'}"
            )
            state.setProperty("coverageCovered", item.covered)
            layout.addWidget(title)
            layout.addWidget(state)

            self._layout.addWidget(tile, index // 5, index % 5)
            self._labels.append(state)


def make_coverage_card(title: str = "Group Buff & Provider Coverage") -> tuple[FoundryCard, TeamCoverageGrid]:
    card = FoundryCard(title, "◈")
    subtitle = QLabel(
        "The same scoreboard appears before and after optimization so coverage gains stay visible."
    )
    subtitle.setWordWrap(True)
    card.addWidget(subtitle)
    grid = TeamCoverageGrid()
    card.addWidget(grid)
    return card, grid
