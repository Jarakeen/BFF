from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_static_build_context_service import RotationStaticBuildContextService


class _ProgressionAdapter:
    def __init__(self, resolution: SavedBuildProgressionResolution) -> None:
        self.resolution = resolution
        self.calls = []

    def resolve(self, build):
        self.calls.append(build)
        return self.resolution


class _ContextFactory:
    def __init__(self, unresolved_by_bar=None) -> None:
        self.unresolved_by_bar = dict(unresolved_by_bar or {})
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        bar = kwargs["active_bar"]
        return SimpleNamespace(
            active_bar=bar,
            unresolved_gear_effects=tuple(self.unresolved_by_bar.get(bar, ())),
            character_state=SimpleNamespace(
                max_health=21000,
                max_magicka=32000 if bar == "front" else 31800,
                max_stamina=13000,
            ),
            core_state=SimpleNamespace(),
        )


def _progression(*, unresolved=()) -> SavedBuildProgressionResolution:
    return SavedBuildProgressionResolution(
        character_id="character-1" if not unresolved else "",
        progression=CharacterProgression(
            attributes=AttributeAllocation(health=0, magicka=64, stamina=0),
            owned_skill_lines=frozenset({"Light Armor", "Medium Armor", "Undaunted"}),
            passive_ranks={
                "Evocation": 2,
                "Concentration": 2,
                "Prodigy": 2,
                "Wind Walker": 2,
                "Dexterity": 2,
                "Undaunted Mettle": 2,
            },
            passive_cp_points={},
        ),
        unresolved=tuple(unresolved),
    )


def _build() -> PlayerBuild:
    return PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")


def test_resolves_front_and_back_with_one_canonical_progression_snapshot() -> None:
    build = _build()
    adapter = _ProgressionAdapter(_progression())
    factory = _ContextFactory()
    service = RotationStaticBuildContextService(
        progression_adapter=adapter,
        context_factory=factory,
    )

    result = service.resolve(build)

    assert result.resolved is True
    assert result.unresolved == ()
    assert adapter.calls == [build]
    assert [call["active_bar"] for call in factory.calls] == ["front", "back"]
    assert all(call["character_id"] == "character-1" for call in factory.calls)
    assert all(call["build"] is build for call in factory.calls)
    assert all(call["progression"] is adapter.resolution.progression for call in factory.calls)
    assert result.context_for("front").character_state.max_magicka == 32000
    assert result.context_for("BACK").character_state.max_magicka == 31800


def test_static_resource_ceiling_preserves_bar_specific_values_and_only_unifies_when_safe() -> None:
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(_progression()),
        context_factory=_ContextFactory(),
    )

    result = service.resolve(_build())

    assert result.maximum_amounts_for(ResourceType.MAGICKA) == (
        ("front", 32000),
        ("back", 31800),
    )
    assert result.uniform_maximum_amount_for(ResourceType.MAGICKA) is None
    assert result.maximum_amounts_for(ResourceType.STAMINA) == (
        ("front", 13000),
        ("back", 13000),
    )
    assert result.uniform_maximum_amount_for(ResourceType.STAMINA) == 13000
    assert result.uniform_maximum_amount_for(ResourceType.HEALTH) == 21000


def test_unresolved_progression_fails_closed_before_static_calculation() -> None:
    build = _build()
    adapter = _ProgressionAdapter(
        _progression(unresolved=("Canonical character progression could not be resolved",))
    )
    factory = _ContextFactory()
    service = RotationStaticBuildContextService(
        progression_adapter=adapter,
        context_factory=factory,
    )

    result = service.resolve(build)

    assert result.resolved is False
    assert result.contexts == ()
    assert result.unresolved == (
        "Canonical character progression could not be resolved",
    )
    assert factory.calls == []


def test_static_context_unresolved_evidence_is_bar_scoped_and_blocks_resolution() -> None:
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(_progression()),
        context_factory=_ContextFactory(
            {
                "front": ("Passive rank is not recorded for character: Prodigy",),
                "back": ("Passive rank is not recorded for character: Prodigy",),
            }
        ),
    )

    result = service.resolve(_build())

    assert result.resolved is False
    assert result.unresolved == (
        "front static context: Passive rank is not recorded for character: Prodigy",
        "back static context: Passive rank is not recorded for character: Prodigy",
    )
    assert len(result.contexts) == 2


def test_requested_bar_subset_is_normalized_and_deduplicated() -> None:
    factory = _ContextFactory()
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(_progression()),
        context_factory=factory,
    )

    result = service.resolve(_build(), bars=("BACK", "back"))

    assert result.resolved is True
    assert [context.active_bar for context in result.contexts] == ["back"]
    assert result.context_for("front") is None
    assert result.uniform_maximum_amount_for(ResourceType.MAGICKA) == 31800


def test_invalid_or_empty_bar_scope_fails_closed() -> None:
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(_progression()),
        context_factory=_ContextFactory(),
    )

    with pytest.raises(ValueError, match="front or back"):
        service.resolve(_build(), bars=("sideways",))
    with pytest.raises(ValueError, match="at least one bar"):
        service.resolve(_build(), bars=())
