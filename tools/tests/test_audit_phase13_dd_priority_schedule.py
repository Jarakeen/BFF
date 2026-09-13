from types import SimpleNamespace

import pytest

from tools.audit_phase13_dd_priority_schedule import _parse_priority, _priority_entries


def _build():
    return SimpleNamespace(
        FrontBarSkills=[
            "Venom Skull",
            "Blighted Blastbones",
            "Unnerving Boneyard",
            "Detonating Siphon",
            "Magical Banner",
        ],
        BackBarSkills=[
            "Skeletal Archer",
            "Scalding Rune",
            "Stampede",
            "Resolving Vigor",
            "Magical Banner",
        ],
    )


def test_parse_priority_resolves_skill_name_from_saved_slot() -> None:
    entry = _parse_priority("front:2:1", build=_build())

    assert entry.bar == "front"
    assert entry.slot == 2
    assert entry.skill_name == "Blighted Blastbones"
    assert entry.priority == 1


def test_priority_entries_require_complete_ordinary_saved_bar_coverage() -> None:
    with pytest.raises(ValueError, match="missing front slot 2: Blighted Blastbones"):
        _priority_entries(("front:1:1",), build=_build())


def test_priority_entries_accept_complete_two_bar_ranking() -> None:
    raw = tuple(
        [f"front:{slot}:{slot}" for slot in range(1, 6)]
        + [f"back:{slot}:{slot + 5}" for slot in range(1, 6)]
    )

    entries = _priority_entries(raw, build=_build())

    assert len(entries) == 10
    assert entries[0].skill_name == "Venom Skull"
    assert entries[-1].skill_name == "Magical Banner"
