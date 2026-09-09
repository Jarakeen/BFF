from types import SimpleNamespace

from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage
from ui.rotation_encounter_selector_support import RotationEncounterSelectorSupport


class _Combo:
    def __init__(self) -> None:
        self.items: list[tuple[str, object]] = []
        self.index = -1

    def blockSignals(self, _blocked: bool) -> None:
        pass

    def clear(self) -> None:
        self.items.clear()
        self.index = -1

    def addItem(self, label: str, data=None) -> None:
        self.items.append((label, data))
        if self.index < 0:
            self.index = 0

    def currentData(self):
        if 0 <= self.index < len(self.items):
            return self.items[self.index][1]
        return None

    def findData(self, data) -> int:
        for index, (_label, value) in enumerate(self.items):
            if value == data:
                return index
        return -1

    def setCurrentIndex(self, index: int) -> None:
        self.index = index

    def currentIndex(self) -> int:
        return self.index

    def count(self) -> int:
        return len(self.items)


class _GuideService:
    def __init__(self, summaries) -> None:
        self.summaries = tuple(summaries)
        self.calls = 0

    def encounter_summaries(self):
        self.calls += 1
        return self.summaries


def _page() -> SimpleNamespace:
    return SimpleNamespace(
        rotation_content_combo=_Combo(),
        rotation_boss_combo=_Combo(),
    )


def _summary(encounter_id: str, name: str, content_id: str, content_name: str):
    return SimpleNamespace(
        encounter_id=encounter_id,
        name=name,
        content_id=content_id,
        content_name=content_name,
    )


def test_selector_deduplicates_content_and_filters_bosses_by_canonical_content_id() -> None:
    service = _GuideService(
        (
            _summary("lokke", "Lokkestiiz", "sunspire", "Sunspire"),
            _summary("yolna", "Yolnahkriin", "sunspire", "Sunspire"),
            _summary("taleria", "Taleria", "dreadsail_reef", "Dreadsail Reef"),
        )
    )
    selector = RotationEncounterSelectorSupport(service)
    page = _page()

    selector.refresh(page)

    assert service.calls == 1
    assert page.rotation_content_combo.items == [
        ("All Content", None),
        ("Sunspire", "sunspire"),
        ("Dreadsail Reef", "dreadsail_reef"),
    ]
    assert [data for _label, data in page.rotation_boss_combo.items] == [
        "lokke",
        "yolna",
        "taleria",
    ]

    page.rotation_content_combo.setCurrentIndex(1)
    selector.populate_bosses(page)

    assert page.rotation_boss_combo.items == [
        ("Lokkestiiz", "lokke"),
        ("Yolnahkriin", "yolna"),
    ]


def test_selector_preserves_selected_encounter_id_when_refresh_still_contains_it() -> None:
    service = _GuideService(
        (
            _summary("lokke", "Lokkestiiz", "sunspire", "Sunspire"),
            _summary("yolna", "Yolnahkriin", "sunspire", "Sunspire"),
        )
    )
    selector = RotationEncounterSelectorSupport(service)
    page = _page()
    selector.refresh(page)
    page.rotation_content_combo.setCurrentIndex(1)
    selector.populate_bosses(page, preferred_encounter_id="yolna")

    selector.refresh(page)

    assert selector.selected_encounter_id(page) == "yolna"


def test_selector_returns_none_when_no_encounter_is_available() -> None:
    selector = RotationEncounterSelectorSupport(_GuideService(()))
    page = _page()

    selector.refresh(page)

    assert page.rotation_content_combo.items == [("All Content", None)]
    assert page.rotation_boss_combo.items == []
    assert selector.selected_encounter_id(page) is None


def test_dashboard_selected_encounter_id_delegates_to_selector_without_inference() -> None:
    selector = SimpleNamespace(selected_encounter_id=lambda page: "xalvakka")
    page = SimpleNamespace(rotation_encounter_selector=selector)

    selected = CanonicalRotationDashboardPage.selected_encounter_id(page)

    assert selected == "xalvakka"
