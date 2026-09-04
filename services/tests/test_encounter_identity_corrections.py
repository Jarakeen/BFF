from services.encounter_boss_guide import BossGuideEncounterSummary
from services.encounter_identity_corrections import (
    boss_title_is_excluded,
    encounter_identity_is_excluded,
)
from ui.encounter_identity_correction_support import _filter_summaries


def _summary(content_id: str, encounter_id: str, name: str) -> BossGuideEncounterSummary:
    return BossGuideEncounterSummary(
        encounter_id=encounter_id,
        content_id=content_id,
        content_name=content_id.replace("_", " ").title(),
        name=name,
        location="",
    )


def test_blackheart_generic_creature_pages_are_not_boss_identities() -> None:
    assert encounter_identity_is_excluded("blackheart_haven", "ogrim") is True
    assert encounter_identity_is_excluded("blackheart_haven", "hagraven") is True
    assert encounter_identity_is_excluded("blackheart_haven", "skeleton") is True
    assert boss_title_is_excluded("blackheart_haven", "Ogrim") is True


def test_named_blackheart_bosses_are_not_excluded() -> None:
    assert encounter_identity_is_excluded("blackheart_haven", "atarus") is False
    assert encounter_identity_is_excluded("blackheart_haven", "roost_mother") is False
    assert encounter_identity_is_excluded("blackheart_haven", "captain_blackheart") is False


def test_same_generic_name_elsewhere_is_not_globally_hidden() -> None:
    assert encounter_identity_is_excluded("some_other_content", "ogrim") is False
    assert boss_title_is_excluded("some_other_content", "Ogrim") is False


def test_boss_guide_filter_removes_only_reviewed_false_blackheart_rows() -> None:
    rows = (
        _summary("blackheart_haven", "atarus", "Atarus"),
        _summary("blackheart_haven", "ogrim", "Ogrim"),
        _summary("blackheart_haven", "roost_mother", "Roost Mother"),
        _summary("blackheart_haven", "hagraven", "Hagraven"),
        _summary("blackheart_haven", "captain_blackheart", "Captain Blackheart"),
        _summary("blackheart_haven", "skeleton", "Skeleton"),
        _summary("other_content", "ogrim", "Ogrim"),
    )

    filtered = _filter_summaries(rows)

    assert [(row.content_id, row.encounter_id) for row in filtered] == [
        ("blackheart_haven", "atarus"),
        ("blackheart_haven", "roost_mother"),
        ("blackheart_haven", "captain_blackheart"),
        ("other_content", "ogrim"),
    ]
