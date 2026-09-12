from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from minmax.stat_ids import StatId
from models.build_model import BuildRoster, PlayerBuild
from ui.foundry_page import FoundryPage
from ui.builds_page import BuildsPage
from ui.operations_console import OperationsConsole, OverviewRing


def _console(tmp_path):
    QApplication.instance() or QApplication([])
    page = OperationsConsole.__new__(OperationsConsole)
    FoundryPage.__init__(page)
    page.roster = BuildRoster(Members=[PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")])
    page._render = lambda: None
    page._selected_build = lambda: page.roster.Members[0]
    return page


def test_unmapped_or_conditional_effect_never_becomes_confirmed_coverage(tmp_path, monkeypatch):
    from ui import operations_console

    database = tmp_path / "eso.db"
    database.touch()
    monkeypatch.setattr(operations_console, "DEFAULT_DATABASE", database)
    page = _console(tmp_path)
    page.capability_service = SimpleNamespace(audit_build=lambda _build: SimpleNamespace(
        resolved_effects=(
            SimpleNamespace(name="major_courage", condition=None, trigger=None),
            SimpleNamespace(name="major_slayer", condition="on ultimate use", trigger=None),
            SimpleNamespace(name="force", condition=None, trigger=None),
        ),
        capability_unresolved=(),
    ))
    page.build_service = object()
    status, providers = page._coverage()

    assert status["Major Courage"] == "available"
    assert providers["Major Courage"] == ["Magrat"]
    assert status["Major Slayer"] == "conditional"
    assert status["War Horn"] == "unverified"
    assert status["Orbs"] == "unverified"
    assert status["Minor Brittle"] == "not_found"


def test_unknown_coverage_is_summarized_without_claiming_missing_providers(tmp_path):
    page = _console(tmp_path)
    from ui.operations_console import CORE_COVERAGE

    states = {name: "unverified" for name in CORE_COVERAGE}
    providers = {name: [] for name in CORE_COVERAGE}
    coverage = page._coverage_card(states, providers)
    checks = page._warnings_card(states)
    coverage_text = " ".join(label.text() for label in coverage.findChildren(QLabel))
    checks_text = " ".join(label.text() for label in checks.findChildren(QLabel))

    assert "15 effects unverified" in coverage_text
    assert any(button.text() == "View Coverage Details" for button in coverage.findChildren(QPushButton))
    assert "?  Major Courage" not in coverage_text
    assert "Coverage evidence incomplete" in checks_text
    assert "Major Courage" not in checks_text


def test_raid_status_reflects_selected_saved_build_ready_flag(tmp_path):
    page = _console(tmp_path)
    card = page._raid_status_card()
    assert "Not marked ready" in " ".join(label.text() for label in card.findChildren(QLabel))
    page.roster.Members[0].ReadyForRaid = True
    card = page._raid_status_card()
    assert "Ready saved builds: 1 / 1" in " ".join(label.text() for label in card.findChildren(QLabel))


def test_builds_ready_checkbox_saves_selected_build(tmp_path):
    QApplication.instance() or QApplication([])
    page = BuildsPage.__new__(BuildsPage)
    FoundryPage.__init__(page)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    saved = []
    page._save = lambda: saved.append(build.ReadyForRaid)
    header = page._identity_header("Magrat", "Healer", build)
    checkbox = header.findChild(QCheckBox)
    assert checkbox.text() == "Ready" and not checkbox.isChecked()
    checkbox.setChecked(True)
    assert saved == [True] and build.ReadyForRaid


def test_key_stats_use_canonical_context_fields_instead_of_missing_stats_property(tmp_path):
    page = _console(tmp_path)
    context = SimpleNamespace(
        character_state=SimpleNamespace(max_health=30000, max_magicka=32000, max_stamina=18000),
        unresolved_gear_effects=(),
        core_state=SimpleNamespace(derived={
            StatId.WEAPON_DAMAGE: SimpleNamespace(final_value=4123),
            StatId.SPELL_DAMAGE: SimpleNamespace(final_value=4267),
            StatId.PHYSICAL_PENETRATION: SimpleNamespace(final_value=2200),
            StatId.SPELL_PENETRATION: SimpleNamespace(final_value=2500),
        }),
    )
    page.context_factory = SimpleNamespace(build=lambda **_kwargs: context)
    card = page._key_stats_card(page.roster.Members[0])
    text = " ".join(label.text() for label in card.findChildren(QLabel))
    assert "30,000" in text and "4,267" in text and "2,500" in text
    assert "unavailable" not in text.lower()


def test_main_dashboard_keeps_four_cards_per_row_without_horizontal_scroll(tmp_path):
    from ui.operations_console import CORE_COVERAGE

    page = _console(tmp_path)
    page.roster.Members[0].AttributeMagicka = 64
    page.expedition = SimpleNamespace(expedition=SimpleNamespace(Expedition="", Difficulty="", Objective=""))
    page.build_service = SimpleNamespace(load=lambda: page.roster)
    page.context_factory = SimpleNamespace(build=lambda **_kwargs: (_ for _ in ()).throw(ValueError("unavailable")))
    page._coverage = lambda: ({name: "unverified" for name in CORE_COVERAGE}, {name: [] for name in CORE_COVERAGE})
    page._capability_audits = {}
    del page._render  # Use the actual dashboard renderer instead of _console's test stub.
    page._build_ui()
    page.refresh()

    for width in (1200, 1366, 1918):
        page.resize(width, 900)
        page.show()
        QApplication.processEvents()
        assert page.workspace_scroll.horizontalScrollBar().maximum() == 0
        for row in (page._hero_cards, page._detail_cards, page._goal_cards):
            assert len(row) == 4
            assert len({card.y() for card in row}) == 1

    bars = page._hero_cards[0].findChildren(QProgressBar)
    assert [bar.property("overviewAttribute") for bar in bars] == ["health", "stamina", "magicka"]
    assert [bar.width() for bar in bars] == [96, 96, 96]
    assert [bar.value() for bar in bars] == [0, 0, 64]
    assert "BOOKMARKS" in " ".join(label.text() for label in page._detail_cards[2].findChildren(QLabel))


def test_attribute_meters_have_distinct_colors_in_both_themes(tmp_path):
    from ui.grimoire_theme import load_grimoire_stylesheet
    from ui.theme.theme_manager import FOUNDRY_OVERVIEW_ACCENTS, RYLO_GRAYSCALE_OVERRIDES

    app = QApplication.instance() or QApplication([])
    old_stylesheet = app.styleSheet()
    page = _console(tmp_path)
    page.roster.Members[0].AttributeHealth = 22
    page.roster.Members[0].AttributeStamina = 44
    page.roster.Members[0].AttributeMagicka = 60
    workspace = QWidget()
    workspace.setProperty("operationsOverview", True)
    workspace.setLayout(QVBoxLayout())
    workspace.layout().addWidget(page._player_card(page.roster.Members[0]))
    try:
        for css, expected in (
            (FOUNDRY_OVERVIEW_ACCENTS, ("#c96569", "#78b887", "#73a9d8")),
            (RYLO_GRAYSCALE_OVERRIDES, ("#c48a83", "#9dac85", "#86accf")),
        ):
            app.setStyleSheet(load_grimoire_stylesheet() + "\n" + css)
            workspace.resize(380, 340)
            workspace.show()
            app.processEvents()
            colors = tuple(bar.grab().toImage().pixelColor(10, 6).name() for bar in workspace.findChildren(QProgressBar))
            assert colors == expected
    finally:
        app.setStyleSheet(old_stylesheet)


def test_progress_and_bookmark_cards_use_loaded_profile_sources(tmp_path):
    page = _console(tmp_path)
    host = QWidget()
    page.setParent(host)
    progress = SimpleNamespace(active_profile="Keen", reload=lambda **_kw: None)
    stats = SimpleNamespace(
        top_categories=lambda: ["Trials"],
        overall=lambda: {"count_earned": 15, "count_total": 100},
        category=lambda _name: {"count_earned": 3, "count_total": 10},
    )
    sticker = SimpleNamespace(profile_id="Keen", service=SimpleNamespace(summary=lambda profile: (25, 50)))
    profile = QComboBox()
    profile.addItem("Keen")
    gear = SimpleNamespace(
        gear_bookmark_profile=profile,
        gear_bookmark_service=SimpleNamespace(
            bookmarked_set_ids=lambda _profile: {42}, note=lambda _profile, _set: "Raid support"
        ),
        _sets=[{"gear_set_id": 42, "name": "Pearls of Ehlnofey"}],
    )
    host.pages = {
        "achievements": SimpleNamespace(achievement_progress_service=progress, achievement_stats_service=stats),
        "stickerbook": sticker,
        "gear_lookup": gear,
    }
    host.collectible_service = SimpleNamespace(
        active_profile="Keen", progress_summary=lambda category: (4, 8)
    )

    achievements = page._achievements_card()
    achievement_text = " ".join(label.text() for label in achievements.findChildren(QLabel))
    assert "Profile: Keen" in achievement_text
    assert "15 / 100 completed" in achievement_text
    assert "Godslayer" not in achievement_text

    collectibles = page._collectibles_card()
    rings = collectibles.findChildren(OverviewRing)
    assert {(ring.label, ring.percent, ring.detail) for ring in rings} == {
        ("Sticker Book", 50, "25 / 50"), ("Mounts", 50, "4 / 8")
    }

    bookmarks = page._bookmarked_gear_card()
    bookmark_text = " ".join(label.text() for label in bookmarks.findChildren(QLabel))
    assert "Pearls of Ehlnofey" in bookmark_text and "Raid support" in bookmark_text
    assert "Spell Power Cure" not in bookmark_text
