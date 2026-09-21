from types import SimpleNamespace

from ui.components.team_progress_panels import (
    DISPLAY_COVERAGE_EFFECTS,
    coverage_from_builds,
    coverage_from_declared_text,
)


def _build(*, name: str, skills=(), sets=(), role="Healer", eso_class="Warden"):
    armor = {
        f"slot-{index}": {"Set": set_name}
        for index, set_name in enumerate(sets)
    }
    return SimpleNamespace(
        Name=name,
        Gamertag="",
        BuildName=f"{name} Build",
        Role=role,
        EsoClass=eso_class,
        FrontBarSkills=list(skills),
        BackBarSkills=[],
        FrontBarWeapon=SimpleNamespace(Set=""),
        BackBarWeapon=SimpleNamespace(Set=""),
        Armor=armor,
    )


def test_declared_composition_coverage_only_checks_explicit_text() -> None:
    rows = (
        ("Main Tank", "Boss control • Major Vulnerability"),
        ("Healer 1", "Raid healing • Major Courage"),
        ("DD 1", "Boss damage"),
    )

    coverage = {item.name: item for item in coverage_from_declared_text(rows)}

    assert tuple(coverage) == DISPLAY_COVERAGE_EFFECTS
    assert coverage["Major Vulnerability"].covered
    assert coverage["Major Vulnerability"].provider == "Main Tank"
    assert coverage["Major Courage"].covered
    assert coverage["Major Courage"].provider == "Healer 1"
    assert not coverage["Major Slayer"].covered


def test_optimization_coverage_resolves_selected_build_evidence() -> None:
    builds = (
        _build(name="Healer", sets=("Spell Power Cure", "Pillager's Profit")),
        _build(name="Tank", skills=("Major Breach", "Unrelenting Grip"), role="Tank"),
    )

    coverage = {item.name: item for item in coverage_from_builds(builds)}

    assert coverage["Major Courage"].covered
    assert coverage["Major Courage"].provider == "Warden Healer"
    assert coverage["Major Slayer"].covered
    assert coverage["Major Slayer"].provider == "Warden Healer"
    assert coverage["Major Breach"].covered
    assert coverage["Major Breach"].provider == "Warden Tank"
    assert not coverage["Major Vulnerability"].covered
