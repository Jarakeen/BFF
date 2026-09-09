from types import SimpleNamespace

import pytest

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeAssessment,
    RotationEffectUptimeRequirement,
)
from services.rotation_support_cadence_effect_evidence_service import (
    RotationSupportCadenceEffectEvidenceService,
)


class _Adapter:
    def __init__(self, adaptation):
        self.adaptation = adaptation
        self.calls = []

    def adapt(self, saved, *, character_id=None):
        self.calls.append((saved, character_id))
        return self.adaptation


class _Uptime:
    def __init__(self):
        self.calls = []

    def assess(self, *, plan, build, requirements, passives=()):
        self.calls.append((plan, build, requirements, tuple(passives)))
        return tuple(
            RotationEffectUptimeAssessment(
                requirement=requirement,
                summary=None,
                unresolved=(f"measured {plan.name}",),
            )
            for requirement in requirements
        )


def _candidate(candidate_id, plan_name):
    return SimpleNamespace(
        candidate_id=candidate_id,
        plan=SimpleNamespace(name=plan_name),
    )


def _requirement():
    return RotationEffectUptimeRequirement(
        effect_name="Minor Berserk",
        source_skill_name="Combat Prayer",
        minimum_uptime=0.90,
        bar="front",
    )


def test_adapts_saved_build_once_and_recomputes_each_candidate_plan() -> None:
    canonical = object()
    adapter = _Adapter(SavedBuildAdaptation(build=canonical, unresolved=("shared note",)))
    uptime = _Uptime()
    service = RotationSupportCadenceEffectEvidenceService(
        build_adapter=adapter,
        uptime_service=uptime,
    )
    saved = object()
    candidates = (
        _candidate("minor_berserk:combat_prayer:full_coverage", "full"),
        _candidate("minor_berserk:combat_prayer:target_floor", "floor"),
    )
    passives = (object(),)

    result = service.assess(
        build=saved,
        candidates=candidates,
        requirements=(_requirement(),),
        passives=passives,
        character_id="Magrat",
    )

    assert adapter.calls == [(saved, "Magrat")]
    assert [call[0].name for call in uptime.calls] == ["full", "floor"]
    assert all(call[1] is canonical for call in uptime.calls)
    assert all(call[3] == passives for call in uptime.calls)
    assert set(result.assessments_by_candidate) == {
        "minor_berserk:combat_prayer:full_coverage",
        "minor_berserk:combat_prayer:target_floor",
    }
    assert result.canonical_build is canonical
    assert result.unresolved == ("shared note",)


def test_failed_canonical_adaptation_preserves_hard_effect_obligations() -> None:
    adapter = _Adapter(
        SavedBuildAdaptation(
            build=None,
            unresolved=("front bar could not be canonicalized",),
        )
    )
    uptime = _Uptime()
    service = RotationSupportCadenceEffectEvidenceService(
        build_adapter=adapter,
        uptime_service=uptime,
    )

    result = service.assess(
        build=object(),
        candidates=(_candidate("candidate-a", "a"),),
        requirements=(_requirement(),),
    )

    assessment = result.assessments_by_candidate["candidate-a"][0]
    assert assessment.observed_uptime is None
    assert assessment.satisfied is False
    assert "front bar could not be canonicalized" in assessment.unresolved[0]
    assert uptime.calls == []
    assert result.canonical_build is None


def test_no_requirements_returns_exact_empty_assessment_map_without_uptime_calls() -> None:
    canonical = object()
    adapter = _Adapter(SavedBuildAdaptation(build=canonical))
    uptime = _Uptime()
    service = RotationSupportCadenceEffectEvidenceService(
        build_adapter=adapter,
        uptime_service=uptime,
    )

    result = service.assess(
        build=object(),
        candidates=(
            _candidate("candidate-a", "a"),
            _candidate("candidate-b", "b"),
        ),
        requirements=(),
    )

    assert result.assessments_by_candidate == {
        "candidate-a": (),
        "candidate-b": (),
    }
    assert uptime.calls == []


def test_duplicate_candidate_ids_are_rejected_case_insensitively() -> None:
    service = RotationSupportCadenceEffectEvidenceService(
        build_adapter=_Adapter(SavedBuildAdaptation(build=object())),
        uptime_service=_Uptime(),
    )

    with pytest.raises(ValueError, match="duplicate.*candidate_id"):
        service.assess(
            build=object(),
            candidates=(
                _candidate("Candidate-A", "a"),
                _candidate("candidate-a", "b"),
            ),
            requirements=(_requirement(),),
        )


def test_blank_candidate_id_is_rejected() -> None:
    service = RotationSupportCadenceEffectEvidenceService(
        build_adapter=_Adapter(SavedBuildAdaptation(build=object())),
        uptime_service=_Uptime(),
    )

    with pytest.raises(ValueError, match="candidate_id must be non-empty"):
        service.assess(
            build=object(),
            candidates=(_candidate("  ", "a"),),
            requirements=(_requirement(),),
        )
