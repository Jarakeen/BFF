from types import SimpleNamespace

from tools.dd_audit_priority_fixture_support import resolve_audit_priorities


def _build():
    return SimpleNamespace(
        FrontBarSkills=["Front One", "Front Two", "", "", ""],
        BackBarSkills=["Back One", "", "", "", ""],
    )


def test_missing_priority_input_uses_deterministic_audit_only_fixture() -> None:
    entries, used_fixture = resolve_audit_priorities((), build=_build())

    assert used_fixture is True
    assert tuple(
        (entry.bar, entry.slot, entry.skill_name, entry.priority)
        for entry in entries
    ) == (
        ("front", 1, "Front One", 1),
        ("front", 2, "Front Two", 2),
        ("back", 1, "Back One", 3),
    )


def test_explicit_priority_input_retains_strict_shared_parser() -> None:
    entries, used_fixture = resolve_audit_priorities(
        (
            "front:1:3",
            "front:2:1",
            "back:1:2",
        ),
        build=_build(),
    )

    assert used_fixture is False
    assert tuple(entry.priority for entry in entries) == (3, 1, 2)
