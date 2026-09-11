from types import SimpleNamespace

import pytest

from services.extreme_resource_active_bar_state_service import (
    ExtremeResourceActiveBarStateService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _active(skill_id, name, line, *, ultimate=False, class_type=""):
    return ExtremePlayerSkillRecord(
        skill_id=skill_id,
        name=name,
        class_type=class_type,
        skill_line=line,
        skill_type="Ultimate" if ultimate else "Active",
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=skill_id,
        max_rank=4,
        max_rank_ability_id=10000 + skill_id,
        description="",
        domain=ExtremeSkillDomain.CLASS if class_type else ExtremeSkillDomain.GUILD,
    )


class _Universe:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def actives(self):
        return self.rows


def _route(*lines):
    # Intentionally omit base-class semantics. The already-validated Extreme
    # route's equipped lines are the subclass legality authority for this layer.
    return SimpleNamespace(equipped_skill_lines=tuple(lines))


def _rows():
    rows = []
    for index in range(5):
        rows.append(_active(10 + index, f"Shadow {index + 1}", "Shadow", class_type="Nightblade"))
        rows.append(_active(20 + index, f"Siphoning {index + 1}", "Siphoning", class_type="Nightblade"))
        rows.append(_active(30 + index, f"Mages {index + 1}", "Mages Guild"))
    rows.extend(
        (
            _active(19, "Shadow Ultimate", "Shadow", ultimate=True, class_type="Nightblade"),
            _active(29, "Siphoning Ultimate", "Siphoning", ultimate=True, class_type="Nightblade"),
            _active(39, "Mages Ultimate", "Mages Guild", ultimate=True),
        )
    )
    return tuple(rows)


def test_max_health_uses_all_six_shadow_slots_for_dark_vigor():
    service = ExtremeResourceActiveBarStateService(skill_universe_service=_Universe(_rows()))

    catalog = service.build("max_health", _route("Shadow", "Earthen Heart", "Ardent Flame"))

    state = catalog.states[0]
    assert catalog.denominator_proven is True
    assert state.shadow_slots == 6
    assert state.siphoning_slots == 0
    assert state.mages_guild_slots == 0
    assert state.reviewed_percent_bonus == pytest.approx(0.30)
    assert all(state.skills)
    assert state.skills[5] == "Shadow Ultimate"


def test_max_magicka_jointly_uses_one_siphoning_and_five_mages_slots():
    service = ExtremeResourceActiveBarStateService(skill_universe_service=_Universe(_rows()))

    catalog = service.build("max_magicka", _route("Siphoning", "Draconic Power", "Storm Calling"))

    state = catalog.states[0]
    assert catalog.denominator_proven is True
    assert state.siphoning_slots == 1
    assert state.mages_guild_slots == 5
    assert state.reviewed_percent_bonus == pytest.approx(0.16)
    assert sum(bool(name) for name in state.skills) == 6


def test_max_magicka_without_siphoning_uses_six_mages_guild_slots():
    service = ExtremeResourceActiveBarStateService(skill_universe_service=_Universe(_rows()))

    catalog = service.build("max_magicka", _route("Shadow", "Earthen Heart", "Storm Calling"))

    state = catalog.states[0]
    assert state.siphoning_slots == 0
    assert state.mages_guild_slots == 6
    assert state.reviewed_percent_bonus == pytest.approx(0.12)


def test_max_stamina_needs_only_one_siphoning_witness():
    service = ExtremeResourceActiveBarStateService(skill_universe_service=_Universe(_rows()))

    catalog = service.build("max_stamina", _route("Siphoning", "Earthen Heart", "Storm Calling"))

    state = catalog.states[0]
    assert state.siphoning_slots == 1
    assert state.mages_guild_slots == 0
    assert state.reviewed_percent_bonus == pytest.approx(0.06)
    assert sum(bool(name) for name in state.skills) == 1


def test_empty_skill_universe_fails_closed():
    service = ExtremeResourceActiveBarStateService(skill_universe_service=_Universe(()))

    catalog = service.build("max_health", _route("Shadow"))

    assert catalog.denominator_proven is False
    assert catalog.unresolved


def test_materialize_writes_only_selected_active_bar():
    from models.build_model import PlayerBuild

    service = ExtremeResourceActiveBarStateService(skill_universe_service=_Universe(_rows()))
    state = service.build("max_stamina", _route("Siphoning")).states[0]
    build = PlayerBuild()
    build.FrontBarSkills[0] = "front-existing"
    build.BackBarSkills[0] = "back-existing"

    result = service.materialize(build, state, active_bar="back")

    assert result.FrontBarSkills[0] == "front-existing"
    assert result.BackBarSkills[0].startswith("Siphoning")
