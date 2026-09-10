from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_sorcerer_blood_magic_service import (
    ExtremeSorcererBloodMagicService,
)


class _SkillLines:
    lines = {
        "Dark Exchange": "Dark Magic",
        "Combat Prayer": "Restoration Staff",
    }

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Blood Magic" else None


def _service():
    return ExtremeSorcererBloodMagicService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def _context(*, health=24000, magicka=32000, stamina=18000):
    return SimpleNamespace(
        character_state=SimpleNamespace(
            max_health=health,
            max_magicka=magicka,
            max_stamina=stamina,
        )
    )


def _resolve(**kwargs):
    values = dict(
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=CharacterProgression(passive_ranks={"Blood Magic": 2}),
        context=_context(),
        trigger_ability_name="Dark Exchange",
        trigger_ability_has_cost=True,
        caster_health_fraction=1.0,
    )
    values.update(kwargs)
    return _service().resolve(**values)


def test_blood_magic_injured_branch_resolves_separate_max_health_scaled_self_heal():
    result = _resolve(
        context=_context(health=24000),
        caster_health_fraction=0.75,
    )

    assert result.branch == "self_heal"
    assert result.self_heal == pytest.approx(2400.0)
    assert result.resource_stat is None
    assert result.resource_percent == 0.0
    assert result.duration_seconds is None
    assert result.unresolved == ()


def test_blood_magic_full_health_branch_selects_higher_resource_for_ten_seconds():
    magicka = _resolve(context=_context(magicka=32000, stamina=18000))
    stamina = _resolve(context=_context(magicka=17000, stamina=30000))

    assert magicka.branch == "resource_window"
    assert magicka.resource_stat == "max_magicka"
    assert magicka.resource_percent == pytest.approx(0.10)
    assert magicka.duration_seconds == pytest.approx(10.0)
    assert magicka.self_heal is None
    assert magicka.unresolved == ()

    assert stamina.resource_stat == "max_stamina"
    assert stamina.resource_percent == pytest.approx(0.10)


def test_blood_magic_equal_resources_fail_closed_instead_of_guessing():
    result = _resolve(context=_context(magicka=25000, stamina=25000))

    assert result.branch == "resource_window"
    assert result.resource_stat is None
    assert result.resource_percent == pytest.approx(0.10)
    assert result.unresolved == (
        "Blood Magic higher-resource branch is ambiguous because Max Magicka and Max Stamina are equal",
    )


def test_blood_magic_requires_costed_dark_magic_trigger():
    wrong_line = _resolve(trigger_ability_name="Combat Prayer")
    no_cost = _resolve(trigger_ability_has_cost=False)

    assert wrong_line.branch is None
    assert "requires a Dark Magic triggering ability" in wrong_line.unresolved[0]
    assert no_cost.branch is None
    assert no_cost.unresolved == (
        "Blood Magic requires a triggering Dark Magic ability with a cost",
    )


def test_blood_magic_respects_subclass_route_and_passive_rank_evidence():
    removed = _resolve(
        build=PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Daedric Summoning", "Storm Calling", "Green Balance"],
        )
    )
    foreign = _resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Dark Magic"],
        )
    )
    partial = _resolve(
        progression=CharacterProgression(passive_ranks={"Blood Magic": 1})
    )

    assert removed.branch is None
    assert removed.unresolved == ()
    assert foreign.branch == "resource_window"
    assert foreign.resource_stat == "max_magicka"
    assert partial.branch is None
    assert partial.unresolved == (
        "Partial passive rank is not yet modeled: Blood Magic 1/2",
    )
