import services.extreme_hypothetical_racial_progression_service as racial_module
from minmax.character_progression import AttributeAllocation, CharacterProgression
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _racial(name: str, line: str, rank: int) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=rank,
        name=name,
        class_type="",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=rank,
        max_rank_ability_id=None,
        description="",
        domain=ExtremeSkillDomain.RACIAL,
    )


class _Universe:
    def passives(self):
        return (
            _racial("Syrabane's Boon", "High Elf Skills", 3),
            _racial("Spell Recharge", "High Elf Skills", 3),
            _racial("Resist Affliction", "Wood Elf Skills", 3),
            _racial("Hunter's Eye", "Wood Elf Skills", 3),
            _racial("Dynamic", "Dark Elf Skills", 3),
            _racial("Ruination", "Dark Elf Skills", 3),
            _racial("Tough", "Imperial Skills", 3),
        )


def _progression() -> CharacterProgression:
    return CharacterProgression(
        attributes=AttributeAllocation(health=64, magicka=0, stamina=0),
        owned_skill_lines=("Undaunted", "High Elf Skills"),
        passive_ranks={
            "Undaunted Mettle": 2,
            "Syrabane's Boon": 1,
            "Spell Recharge": 2,
            "Tough": 3,
        },
        passive_cp_points={},
    )


def test_normalize_replaces_inherited_race_with_selected_max_rank_racial_progression():
    service = ExtremeHypotheticalRacialProgressionService(universe_service=_Universe())

    result = service.normalize(_progression(), "Wood Elf")

    assert result.passive_rank("Undaunted Mettle") == 2
    assert result.passive_rank("Resist Affliction") == 3
    assert result.passive_rank("Hunter's Eye") == 3
    assert result.passive_rank("Syrabane's Boon") is None
    assert result.passive_rank("Spell Recharge") is None
    assert result.passive_rank("Tough") is None
    assert result.owns_skill_line("Undaunted") is True
    assert result.owns_skill_line("Wood Elf Skills") is True
    assert result.owns_skill_line("High Elf Skills") is False


def test_normalize_maps_altmer_to_high_elf_skill_line():
    service = ExtremeHypotheticalRacialProgressionService(universe_service=_Universe())

    result = service.normalize(_progression(), "Altmer")

    assert result.passive_rank("Syrabane's Boon") == 3
    assert result.passive_rank("Spell Recharge") == 3
    assert result.owns_skill_line("High Elf Skills") is True


def test_normalize_maps_bosmer_to_wood_elf_skill_line():
    service = ExtremeHypotheticalRacialProgressionService(universe_service=_Universe())

    result = service.normalize(_progression(), "Bosmer")

    assert result.passive_rank("Resist Affliction") == 3
    assert result.passive_rank("Hunter's Eye") == 3
    assert result.owns_skill_line("Wood Elf Skills") is True
    assert result.owns_skill_line("High Elf Skills") is False


def test_normalize_maps_dunmer_to_dark_elf_skill_line():
    service = ExtremeHypotheticalRacialProgressionService(universe_service=_Universe())

    result = service.normalize(_progression(), "Dunmer")

    assert result.passive_rank("Dynamic") == 3
    assert result.passive_rank("Ruination") == 3
    assert result.owns_skill_line("Dark Elf Skills") is True
    assert result.owns_skill_line("High Elf Skills") is False


def test_normalize_fails_closed_when_race_has_no_canonical_passives():
    service = ExtremeHypotheticalRacialProgressionService(universe_service=_Universe())

    try:
        service.normalize(_progression(), "Mystery Elf")
    except ValueError as exc:
        assert "canonical racial passives not found" in str(exc)
    else:
        raise AssertionError("expected missing racial progression to fail closed")


def test_normalize_fails_closed_when_selected_passive_has_no_max_rank():
    class _BrokenUniverse:
        def passives(self):
            return (_racial("Broken Boon", "High Elf Skills", 0),)

    service = ExtremeHypotheticalRacialProgressionService(universe_service=_BrokenUniverse())
    try:
        service.normalize(_progression(), "High Elf")
    except ValueError as exc:
        assert "canonical max rank unavailable" in str(exc)
    else:
        raise AssertionError("expected missing max-rank evidence to fail closed")


def test_production_services_share_racial_passive_projection_per_database(tmp_path, monkeypatch):
    database = tmp_path / "eso.db"
    database.touch()
    calls = {"passives": 0}

    class _CountingUniverse:
        def __init__(self, database_path):
            self.database_path = database_path

        def passives(self):
            calls["passives"] += 1
            return _Universe().passives()

    racial_module._RACIAL_PASSIVE_CACHE.clear()
    monkeypatch.setattr(racial_module, "ExtremeSkillUniverseService", _CountingUniverse)

    first = racial_module.ExtremeHypotheticalRacialProgressionService(database)
    second = racial_module.ExtremeHypotheticalRacialProgressionService(database)

    assert first.normalize(_progression(), "Altmer").passive_rank("Syrabane's Boon") == 3
    assert second.normalize(_progression(), "Bosmer").passive_rank("Hunter's Eye") == 3
    assert calls["passives"] == 1
