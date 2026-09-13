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


def test_race_projection_collapses_equal_target_resource_signatures():
    service = ExtremeResourceRaceProjectionService(
        "unused.db",
        progression_service=_ProgressionService(),
        racial_repository=_Repository(
            {
                "Breton": RacialPassiveResolution(stats={"max_magicka": 2000.0}),
                "Altmer": RacialPassiveResolution(stats={"max_magicka": 2000.0}),
                "Bosmer": RacialPassiveResolution(stats={"max_magicka": 0.0}),
            }
        ),
    )

    result = service.build("max_magicka", ("Breton", "Altmer", "Bosmer"))

    assert result.projection_complete is True
    assert result.source_race_count == 3
    assert result.signatures == (0.0, 2000.0)
    assert result.races == ("Bosmer", "Altmer")
    assert "3 legal races -> 2 exact witnesses" in result.scope[0]


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
    assert result.unresolved == ("Khajiit: unmapped racial passive",)
