from __future__ import annotations

from services.encounter_boss_guide import (
    BossGuideAbility,
    BossGuideEncounterSummary,
    EncounterBossGuide,
)
from ui.mechanics_boss_map_support import (
    PAIR_ID,
    _merge_pair_guides,
    _paired_summaries,
)


def _summary(encounter_id: str, name: str) -> BossGuideEncounterSummary:
    return BossGuideEncounterSummary(
        encounter_id=encounter_id,
        content_id="dreadsail_reef",
        content_name="Dreadsail Reef",
        name=name,
        location="Dreadsail Reef",
    )


def _guide(encounter_id: str, name: str, health: str, ability: str) -> EncounterBossGuide:
    return EncounterBossGuide(
        encounter_id=encounter_id,
        content_id="dreadsail_reef",
        content_name="Dreadsail Reef",
        name=name,
        summary=f"{name} structural record.",
        location="Dreadsail Reef",
        species="Maormer",
        reaction="Hostile",
        health_record_present=True,
        health=(("veteran", health),),
        abilities=(
            BossGuideAbility(
                ability_id=1 if encounter_id == "lylanar" else 2,
                name=ability,
                description="Source-backed ability.",
                interruptible=None,
                interrupt_note="",
                source_section="Skills and Abilities",
                source_url="",
                source_revision_id="rev",
            ),
        ),
        phases=(),
        structural_phases=(),
        timeline_facts=(),
        source_url="",
        source_page_title=name,
        source_revision_id="rev",
        retrieved_at="",
        source_license="CC BY-SA",
    )


def test_dreadsail_twins_are_one_selector_encounter() -> None:
    rows = (
        _summary("lylanar", "Lylanar"),
        _summary("turlassil", "Turlassil"),
        _summary("reef_guardian", "Reef Guardian"),
    )

    paired = _paired_summaries(rows)

    ids = [row.encounter_id for row in paired]
    assert PAIR_ID in ids
    assert "lylanar" not in ids
    assert "turlassil" not in ids
    combined = next(row for row in paired if row.encounter_id == PAIR_ID)
    assert combined.name == "Lylanar and Turlassil"


def test_dreadsail_twins_merge_structural_guide_data_on_one_page() -> None:
    guide = _merge_pair_guides(
        (
            _guide("lylanar", "Lylanar", "10,000", "Fire Brand"),
            _guide("turlassil", "Turlassil", "11,000", "Frost Brand"),
        )
    )

    assert guide.encounter_id == PAIR_ID
    assert guide.name == "Lylanar and Turlassil"
    assert dict(guide.health)["veteran"] == "Lylanar: 10,000 | Turlassil: 11,000"
    assert [row.name for row in guide.abilities] == [
        "Lylanar • Fire Brand",
        "Turlassil • Frost Brand",
    ]
    assert "Lylanar structural record." in guide.summary
    assert "Turlassil structural record." in guide.summary
