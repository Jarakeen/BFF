from __future__ import annotations

from minmax.gear_set_effect_resolver import GearSetEffectResolver
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
    ExtremeGearSetObjectiveService,
)
from services.extreme_gear_set_resource_effect_resolver import (
    ExtremeGearSetResourceEffectResolver,
)


class _Set:
    id = 1
    name = "Set One"


class _Repository:
    def get_set_by_id(self, set_id):
        return _Set() if int(set_id) == 1 else None


def _catalog():
    return ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(
                set_id=1,
                name="Set One",
                max_equip_count=5,
                bonus_counts=(5,),
            ),
        )
    )


def _candidate(objective_key):
    return ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Set One",
        category="Test",
        equipped_piece_count=5,
        objective_key=objective_key,
        reviewed_delta=0.0,
    )


def test_default_relevance_resolver_uses_resource_adapter_only_for_max_resources(monkeypatch):
    seen = []

    def fake_candidate(repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None):
        seen.append((objective_key, resolver))
        return _candidate(objective_key)

    monkeypatch.setattr(ExtremeGearSetObjectiveService, "candidate_for_set", fake_candidate)

    service = ExtremeGearSetObjectiveRelevanceService(_Repository())
    service.build("max_health", _catalog())
    service.build("spell_damage", _catalog())

    assert isinstance(seen[0][1], ExtremeGearSetResourceEffectResolver)
    assert isinstance(seen[1][1], GearSetEffectResolver)
