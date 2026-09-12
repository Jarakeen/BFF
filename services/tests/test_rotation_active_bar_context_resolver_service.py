from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_active_bar_context_resolver_service import (
    RotationActiveBarContextResolverService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextResolution


def _static_context(*, include_back: bool = True):
    front = SimpleNamespace(active_bar="front", marker="front-context")
    contexts = [front]
    if include_back:
        contexts.append(SimpleNamespace(active_bar="back", marker="back-context"))
    return RotationStaticBuildContextResolution(
        progression=SimpleNamespace(resolved=True),
        contexts=tuple(contexts),
        unresolved=(),
    )


def _plan():
    return RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=12.0,
        actions=(
            RotationAction(2.0, 10, RotationActionKind.SKILL, name="Front Skill", bar="front"),
            RotationAction(4.0, 20, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(4.0, 21, RotationActionKind.SKILL, name="Back Skill", bar="back"),
            RotationAction(8.0, 30, RotationActionKind.BAR_SWAP, bar="front"),
            RotationAction(8.0, 31, RotationActionKind.SKILL, name="Front Again", bar="front"),
        ),
    )


def test_resolves_context_from_exact_time_and_sequence_bar_progression() -> None:
    resolver = RotationActiveBarContextResolverService(
        static_context=_static_context(),
        plan=_plan(),
    )

    assert resolver.active_bar_at(0.0, 0) == "front"
    assert resolver.context_at(2.0, 10).marker == "front-context"
    assert resolver.active_bar_at(4.0, 19) == "front"
    assert resolver.active_bar_at(4.0, 20) == "back"
    assert resolver.context_at(4.0, 21).marker == "back-context"
    assert resolver.active_bar_at(7.999, 999) == "back"
    assert resolver.active_bar_at(8.0, 29) == "back"
    assert resolver.active_bar_at(8.0, 30) == "front"
    assert resolver.context_at(8.0, 31).marker == "front-context"


def test_non_default_initial_bar_is_explicit_and_supported() -> None:
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=5.0,
        actions=(),
    )
    resolver = RotationActiveBarContextResolverService(
        static_context=_static_context(),
        plan=plan,
        initial_bar="BACK",
    )

    assert resolver.active_bar_at(0.0, 0) == "back"
    assert resolver.context_at(3.0, 7).marker == "back-context"


def test_missing_static_destination_bar_fails_closed_at_construction() -> None:
    with pytest.raises(ValueError, match="missing bar: 'back'"):
        RotationActiveBarContextResolverService(
            static_context=_static_context(include_back=False),
            plan=_plan(),
        )


def test_invalid_initial_bar_and_negative_lookup_fail_closed() -> None:
    with pytest.raises(ValueError, match="initial bar must be front or back"):
        RotationActiveBarContextResolverService(
            static_context=_static_context(),
            plan=_plan(),
            initial_bar="sideways",
        )

    resolver = RotationActiveBarContextResolverService(
        static_context=_static_context(),
        plan=_plan(),
    )
    with pytest.raises(ValueError, match="finite and non-negative"):
        resolver.context_at(-0.001, 0)
