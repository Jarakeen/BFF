from minmax.character_progression import CharacterProgression
from minmax.racial_passive_stat_repository import RacialPassiveResolution
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)


class _ProgressionService:
    @staticmethod
    def normalize(_progression, _race):
        return CharacterProgression(passive_ranks={"Reviewed": 3})

    @staticmethod
    def _canonical_skill_line_race(race):
        return race


class _Repository:
    def __init__(self, rows):
        self.rows = rows

    def resolve(self, race, _progression):
        return self.rows[race]


def test_race_projection_keeps_only_strongest_target_resource_witness():
    service = ExtremeResourceRaceProjectionService(
        "unused.db",
        progression_service=_ProgressionService(),
        racial_repository=_Repository(
            {
                "Breton": RacialPassiveResolution(stats={"max_magicka": 2000.0}),
                "Altmer": RacialPassiveResolution(stats={"max_magicka": 2000.0}),
                "Bosmer": RacialPassiveResolution(stats={"max_magicka": 0.0}),
                "Dunmer": RacialPassiveResolution(stats={"max_magicka": 1910.0}),
            }
        ),
    )

    result = service.build(
        "max_magicka",
        ("Breton", "Altmer", "Bosmer", "Dunmer"),
    )

    assert result.projection_complete is True
    assert result.source_race_count == 4
    assert result.signatures == (2000.0,)
    assert result.races == ("Altmer",)
    assert result.source_signatures == (
        ("Breton", 2000.0),
        ("Altmer", 2000.0),
        ("Bosmer", 0.0),
        ("Dunmer", 1910.0),
    )
    assert "4 legal races -> 1 maximum witness" in result.scope[0]


def test_race_projection_fails_closed_when_any_race_is_unresolved():
    service = ExtremeResourceRaceProjectionService(
        "unused.db",
        progression_service=_ProgressionService(),
        racial_repository=_Repository(
            {
                "Breton": RacialPassiveResolution(stats={"max_magicka": 2000.0}),
                "Khajiit": RacialPassiveResolution(
                    stats={},
                    unresolved=("unmapped racial passive",),
                ),
            }
        ),
    )

    result = service.build("max_magicka", ("Breton", "Khajiit"))

    assert result.projection_complete is False
    assert result.denominator_proven is False
    assert result.races == ()
    assert result.unresolved == ("Khajiit: unmapped racial passive",)


def test_race_projection_fails_closed_on_negative_target_resource_value():
    service = ExtremeResourceRaceProjectionService(
        "unused.db",
        progression_service=_ProgressionService(),
        racial_repository=_Repository(
            {
                "Race A": RacialPassiveResolution(stats={"max_magicka": 1000.0}),
                "Race B": RacialPassiveResolution(stats={"max_magicka": -100.0}),
            }
        ),
    )

    result = service.build("max_magicka", ("Race A", "Race B"))

    assert result.projection_complete is False
    assert result.denominator_proven is False
    assert result.races == ()
    assert any("negative" in message for message in result.unresolved)
