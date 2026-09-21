from dataclasses import replace

from minmax.character_progression import CharacterProgression
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_dd_relevant_static_context_service import (
    RotationDDRelevantStaticContextService,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextResolution,
)


class _Delegate:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


def _progression(*, unresolved=()):
    return SavedBuildProgressionResolution(
        character_id="c1",
        progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
        unresolved=tuple(unresolved),
    )


def test_dd_relevant_static_context_drops_reviewed_ambient_diagnostics() -> None:
    delegate = _Delegate(
        RotationStaticBuildContextResolution(
            progression=_progression(),
            contexts=(object(),),
            unresolved=(
                "front static context: movement_speed unresolved",
                "front static context: offensive mechanic unresolved",
            ),
        )
    )

    result = RotationDDRelevantStaticContextService(delegate).resolve(object())

    assert result.unresolved == (
        "front static context: offensive mechanic unresolved",
    )


def test_dd_relevant_static_context_preserves_progression_failures() -> None:
    delegate = _Delegate(
        RotationStaticBuildContextResolution(
            progression=_progression(unresolved=("race unresolved",)),
            contexts=(),
            unresolved=("front static context: movement_speed unresolved",),
        )
    )

    result = RotationDDRelevantStaticContextService(delegate).resolve(object())

    assert result.unresolved == ("race unresolved",)
