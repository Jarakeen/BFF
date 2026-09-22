from __future__ import annotations

from types import SimpleNamespace

from minmax.potion_use_event import PotionTraitUse, PotionUseEvent
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_potion_restoration_evidence_service import (
    RotationCandidatePotionRestorationEvidenceService,
)


class _Resolver:
    def __init__(self, event):
        self.event = event
        self.calls = []

    def resolve(self, name):
        self.calls.append(name)
        return self.event


def _trait(name, magnitude):
    return PotionTraitUse(
        trait=name,
        kind="instant_restore",
        magnitude=magnitude,
        duration=None,
        triple_duration=None,
        tier_name="CP 150",
        solvent="Lorkhan's Tears",
        level=50,
    )


def _event(*traits, unresolved=()):
    return PotionUseEvent(
        selected_label="Potion X",
        traits=tuple(traits),
        unresolved=tuple(unresolved),
    )


def _candidate(*names):
    plan = RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=50.0,
        actions=tuple(
            RotationAction(
                float(index * 45),
                0,
                RotationActionKind.POTION,
                name,
            )
            for index, name in enumerate(names)
        ),
    )
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )


def _build():
    return PlayerBuild(
        Name="Generated",
        BuildName="Candidate",
        Potion="Potion X",
    )


def test_scheduled_potion_uses_emit_all_canonical_instant_restores() -> None:
    resolver = _Resolver(
        _event(
            _trait("Restore Magicka", 7582.0),
            _trait("Restore Stamina", 7582.0),
        )
    )
    result = RotationCandidatePotionRestorationEvidenceService(
        build=_build(),
        event_resolver=resolver,
    ).evaluate_plan(_candidate("Potion X", "Potion X"))

    assert resolver.calls == ["Potion X"]
    assert result.unresolved == ()
    assert tuple(
        (row.time_seconds, row.resource, row.amount)
        for row in result.restoration_events
    ) == (
        (0.0, ResourceType.MAGICKA, 7582),
        (0.0, ResourceType.STAMINA, 7582),
        (45.0, ResourceType.MAGICKA, 7582),
        (45.0, ResourceType.STAMINA, 7582),
    )


def test_no_scheduled_potion_use_emits_no_restoration() -> None:
    resolver = _Resolver(_event(_trait("Restore Magicka", 7582.0)))
    result = RotationCandidatePotionRestorationEvidenceService(
        build=_build(),
        event_resolver=resolver,
    ).evaluate_plan(_candidate())

    assert result.restoration_events == ()
    assert result.unresolved == ()
    assert resolver.calls == []


def test_scheduled_potion_identity_mismatch_fails_closed() -> None:
    resolver = _Resolver(_event(_trait("Restore Magicka", 7582.0)))
    result = RotationCandidatePotionRestorationEvidenceService(
        build=_build(),
        event_resolver=resolver,
    ).evaluate_plan(_candidate("Wrong Potion"))

    assert result.restoration_events
    assert any("does not match saved potion" in row for row in result.unresolved)


def test_unresolved_potion_source_evidence_fails_closed() -> None:
    resolver = _Resolver(
        PotionUseEvent(
            selected_label="Potion X",
            unresolved=("source row missing",),
        )
    )
    result = RotationCandidatePotionRestorationEvidenceService(
        build=_build(),
        event_resolver=resolver,
    ).evaluate_plan(_candidate("Potion X"))

    assert result.restoration_events == ()
    assert result.unresolved == ("source row missing",)


def test_non_integral_restore_magnitude_fails_closed() -> None:
    resolver = _Resolver(_event(_trait("Restore Magicka", 7582.5)))
    result = RotationCandidatePotionRestorationEvidenceService(
        build=_build(),
        event_resolver=resolver,
    ).evaluate_plan(_candidate("Potion X"))

    assert result.restoration_events == ()
    assert any("non-negative integer" in row for row in result.unresolved)
