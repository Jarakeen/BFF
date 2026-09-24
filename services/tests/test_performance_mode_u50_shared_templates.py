from pathlib import Path

from services.build_reuse_service import BuildReuseService


TEMPLATE_PATH = Path("data/build_templates.json")


def test_performance_mode_templates_are_shared_and_loadable() -> None:
    service = BuildReuseService(TEMPLATE_PATH)
    templates = service.load_templates()

    names = {row.name for row in templates}
    assert "PM U50 — Warden Healer — Jarakeen" in names
    assert "PM U50 — Necromancer DD" in names
    assert "PM U50 — Dragonknight Z'enKosh — Cobble" in names
    assert len(templates) >= 10


def test_shared_template_can_apply_to_any_compatible_profile_character() -> None:
    service = BuildReuseService(TEMPLATE_PATH)
    template = next(row for row in service.load_templates() if row.name == "PM U50 — Necromancer DD")

    jarakeen = service.apply_template(
        template,
        destination_name="Jarakeen Necro",
        destination_gamertag="Jarakeen",
        destination_class="Necromancer",
        destination_role="DD",
        new_build_name="PM Necro",
    ).build
    rylo = service.apply_template(
        template,
        destination_name="Rylo Necro",
        destination_gamertag="Rylo",
        destination_class="Necromancer",
        destination_role="DD",
        new_build_name="PM Necro",
    ).build

    assert jarakeen.Gamertag == "Jarakeen"
    assert rylo.Gamertag == "Rylo"
    assert jarakeen.FrontBarSkills == rylo.FrontBarSkills
    assert jarakeen.BackBarSkills == rylo.BackBarSkills
    assert jarakeen.BackBarWeapon.Set == "Perfected Merciless Charge"
    assert jarakeen.PlannedGearSets == ["Corpseburster", "Perfected Slivers of the Null Arca"]


def test_cobble_template_preserves_current_minor_brutality_warning() -> None:
    service = BuildReuseService(TEMPLATE_PATH)
    template = next(
        row for row in service.load_templates()
        if row.name == "PM U50 — Dragonknight Z'enKosh — Cobble"
    )

    assert "Minor Brutality is not guaranteed" in template.notes
    assert "Sundering Knife" in template.class_overlays["Dragonknight"]["FrontBarSkills"]
