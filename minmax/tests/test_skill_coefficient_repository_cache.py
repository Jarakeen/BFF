from __future__ import annotations

from minmax.skill_coefficient_repository import (
    SkillCoefficientRepository,
    SkillRankResolution,
)


class _CountingRepository(SkillCoefficientRepository):
    def __init__(self, database_path) -> None:
        super().__init__(database_path)
        self.scan_count = 0
        self.resolve_count = 0

    def _all_rank_identity_rows(self, connection):
        self.scan_count += 1
        return [{"name": "Combat Prayer"}]

    def _resolve_matching_rows(self, rows, requested, *, label):
        self.resolve_count += 1
        return SkillRankResolution(None, (f"resolved {requested}",))


def test_entity_resolution_is_cached_by_canonical_identity(tmp_path) -> None:
    repository = _CountingRepository(tmp_path / "empty.db")

    first = repository.resolve_entity_id("Combat Prayer")
    second = repository.resolve_entity_id("combat_prayer")
    third = repository.resolve_entity_id("COMBAT-PRAYER")

    assert first == second == third
    assert repository.scan_count == 1
    assert repository.resolve_count == 1


def test_different_entity_ids_are_resolved_independently(tmp_path) -> None:
    repository = _CountingRepository(tmp_path / "empty.db")

    repository.resolve_entity_id("Combat Prayer")
    repository.resolve_entity_id("Radiating Regeneration")

    assert repository.scan_count == 2
    assert repository.resolve_count == 2
