from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from minmax.character_build.character_class import CharacterClass
from services.extreme_maximum_healing_event_finalist_selection_service import (
    ExtremeMaximumHealingEventFinalistSelectionService,
)
from services.extreme_maximum_healing_event_explanation_service import (
    ExtremeMaximumHealingEventTrace,
)


@dataclass(frozen=True)
class _Route:
    base_class: CharacterClass
    equipped_skill_lines: tuple[str, ...]


@dataclass(frozen=True)
class _Entry:
    source_kind: str
    source_name: str
    event_value: float | None
    event_kind: str
    mechanic_complete: bool
    unresolved: tuple[str, ...]
    route: _Route
    slotted_index: int
    trace: ExtremeMaximumHealingEventTrace


def _trace():
    return ExtremeMaximumHealingEventTrace(
        coefficient_numbers=(3,),
        recipient_scopes=("group",),
        recipient_keys=("friendly_targets",),
        event_keys=("pet_special_activation",),
        temporal_scopes=("direct",),
    )


def _entry(lines, *, value=13997.715, slot=0, name="Summon Twilight Matriarch"):
    return _Entry(
        source_kind="ordinary_skill",
        source_name=name,
        event_value=value,
        event_kind="canonical_maximum",
        mechanic_complete=True,
        unresolved=(),
        route=_Route(CharacterClass.WARDEN, tuple(lines)),
        slotted_index=slot,
        trace=_trace(),
    )


def _blood_magic_entry(lines, *, value=9000.0, trigger="Dark Exchange"):
    return _Entry(
        source_kind="blood_magic",
        source_name=f"Blood Magic via {trigger}",
        event_value=value,
        event_kind="normal_noncritical",
        mechanic_complete=True,
        unresolved=(),
        route=_Route(CharacterClass.WARDEN, tuple(lines)),
        slotted_index=0,
        trace=ExtremeMaximumHealingEventTrace(
            recipient_scopes=("self",),
            recipient_keys=("caster",),
            event_keys=("blood_magic_costed_dark_magic_trigger",),
            temporal_scopes=("direct",),
        ),
    )


def test_tied_matriarch_routes_remain_distinct_stage_two_finalists():
    entries = tuple(
        _entry(("animal_companions", "daedric_summoning", third))
        for third in (
            "aedric_spear",
            "green_balance",
            "winters_embrace",
            "restoring_light",
            "siphoning",
        )
    )
    result = SimpleNamespace(entries=entries)

    selected = ExtremeMaximumHealingEventFinalistSelectionService().select(
        result,
        max_families=1,
        routes_per_family=3,
    )

    assert len(selected.finalists) == 3
    assert {entry.route.equipped_skill_lines for entry in selected.finalists} == {
        entries[0].route.equipped_skill_lines,
        entries[1].route.equipped_skill_lines,
        entries[2].route.equipped_skill_lines,
    }
    assert selected.represented_families == 1


def test_exact_duplicate_screen_entries_are_removed_before_shortlisting():
    entry = _entry(("animal_companions", "daedric_summoning", "green_balance"))
    result = SimpleNamespace(entries=(entry, entry))

    selected = ExtremeMaximumHealingEventFinalistSelectionService().select(result)

    assert selected.finalists == (entry,)
    assert selected.exact_duplicates_removed == 1


def test_family_limit_preserves_rank_order_across_distinct_heal_families():
    matriarch = _entry(
        ("animal_companions", "daedric_summoning", "green_balance"),
        value=14000.0,
    )
    combat_prayer = _entry(
        ("animal_companions", "green_balance", "winters_embrace"),
        value=12000.0,
        name="Combat Prayer",
    )
    budding = _entry(
        ("animal_companions", "green_balance", "winters_embrace"),
        value=11000.0,
        name="Budding Seeds",
    )
    result = SimpleNamespace(entries=(matriarch, combat_prayer, budding))

    selected = ExtremeMaximumHealingEventFinalistSelectionService().select(
        result,
        max_families=2,
        routes_per_family=1,
    )

    assert [entry.source_name for entry in selected.finalists] == [
        "Summon Twilight Matriarch",
        "Combat Prayer",
    ]
    assert selected.represented_families == 2


def test_lower_ranked_distinct_source_kind_is_force_included_for_stage_two():
    matriarch = _entry(
        ("animal_companions", "daedric_summoning", "green_balance"),
        value=14000.0,
    )
    twilight = _entry(
        ("animal_companions", "daedric_summoning", "winters_embrace"),
        value=13000.0,
        name="Summon Winged Twilight",
    )
    elder = _entry(
        ("animal_companions", "daedric_summoning", "draconic_power"),
        value=12000.0,
        name="Blood of the Elder Dragon",
    )
    blood_magic = _blood_magic_entry(
        ("animal_companions", "dark_magic", "green_balance"),
        value=8000.0,
    )
    result = SimpleNamespace(entries=(matriarch, twilight, elder, blood_magic))

    selected = ExtremeMaximumHealingEventFinalistSelectionService().select(
        result,
        max_families=3,
        routes_per_family=1,
    )

    assert [entry.source_kind for entry in selected.finalists] == [
        "ordinary_skill",
        "ordinary_skill",
        "ordinary_skill",
        "blood_magic",
    ]
    assert selected.finalists[-1].source_name == "Blood Magic via Dark Exchange"
    assert selected.represented_families == 4
    assert selected.max_families == 3


def test_unscored_entries_never_enter_stage_two_shortlist():
    scored = _entry(("animal_companions", "daedric_summoning", "green_balance"))
    unresolved = _Entry(
        source_kind="ordinary_skill",
        source_name="Unknown Heal",
        event_value=None,
        event_kind="unresolved",
        mechanic_complete=False,
        unresolved=("critical eligibility unresolved",),
        route=_Route(
            CharacterClass.WARDEN,
            ("animal_companions", "green_balance", "winters_embrace"),
        ),
        slotted_index=0,
        trace=ExtremeMaximumHealingEventTrace(),
    )
    result = SimpleNamespace(entries=(scored, unresolved))

    selected = ExtremeMaximumHealingEventFinalistSelectionService().select(result)

    assert selected.finalists == (scored,)
    assert selected.screened_scored_entries == 1
