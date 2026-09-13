from __future__ import annotations

from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL,
    ChampionPointRecord,
    ChampionPointStaticRepository,
)


class _CountingGetRepository(ChampionPointStaticRepository):
    def __init__(self) -> None:
        super().__init__(":memory:")
        self.get_calls = 0
        self._record_cache["Eldritch Insight"] = ChampionPointRecord(
            name="Eldritch Insight",
            skill_type=CHAMPION_SKILL_TYPE_NORMAL,
            max_points=20,
            jump_points=(),
            description="Grants 26 Max Magicka per stage.",
        )

    def get(self, name: str):
        self.get_calls += 1
        return super().get(name)


def test_identical_cp_resolution_reuses_cached_effect_semantics() -> None:
    repository = _CountingGetRepository()

    first_effects, first_unresolved = repository.resolve("Eldritch Insight", 20)
    second_effects, second_unresolved = repository.resolve("Eldritch Insight", 20)

    assert repository.get_calls == 1
    assert first_unresolved == []
    assert second_unresolved == []
    assert first_effects == second_effects
    assert first_effects is not second_effects
    assert first_effects[0].value == 520.0


def test_cp_resolution_cache_keeps_point_allocations_distinct() -> None:
    repository = _CountingGetRepository()

    maxed, _ = repository.resolve("Eldritch Insight", 20)
    partial, _ = repository.resolve("Eldritch Insight", 10)
    partial_again, _ = repository.resolve("Eldritch Insight", 10)

    assert repository.get_calls == 2
    assert maxed[0].value == 520.0
    assert partial[0].value == 260.0
    assert partial_again == partial
