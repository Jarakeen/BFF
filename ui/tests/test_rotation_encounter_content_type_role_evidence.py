from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from services.encounter_boss_guide import EncounterBossGuide
from services.encounter_rotation_demand_service import EncounterRotationDemandService
from ui.rotation_canonical_cadence_orchestration_support import (
    RotationCanonicalCadenceOrchestrationSupport,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import (
    RotationCanonicalEvidenceBundleSupport,
)


class _GuideService:
    def get(self, encounter_id: str) -> EncounterBossGuide:
        return EncounterBossGuide(
            encounter_id=encounter_id,
            content_id="rockgrove",
            content_name="Rockgrove",
            name="Xalvakka",
            summary="",
            location="",
            species="",
            reaction="",
            health_record_present=False,
            health=(),
            abilities=(),
            phases=(),
            structural_phases=(),
            timeline_facts=(),
            source_url="",
            source_page_title="",
            source_revision_id="",
            retrieved_at="",
            source_license="",
            content_type="trial",
        )


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(candidate_result="application")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Render:
    def build(self, _application):
        return None


class _Runner:
    def run(self, **_kwargs):
        raise AssertionError("cadence runner should not be reached")


class _CadenceRender:
    def build(self, _run):
        raise AssertionError("cadence render should not be reached")


def _bundle():
    return RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(),
        demand_service=EncounterRotationDemandService(),
    ).build(
        encounter_id="xalvakka",
        demand_policies=(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )


def _role_evidence(*, content_type: str = "") -> RotationCanonicalRoleEvidence:
    return RotationCanonicalRoleEvidence(
        plan_evidence_provider=object(),  # type: ignore[arg-type]
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        content_type=content_type,
        reliable_group_healing=True,
    )


def _support():
    canonical = _CanonicalCandidates()
    support = RotationCanonicalCadenceOrchestrationSupport(
        canonical_candidates=canonical,  # type: ignore[arg-type]
        canonical_render=_Render(),  # type: ignore[arg-type]
        cadence_runner=_Runner(),  # type: ignore[arg-type]
        cadence_render=_CadenceRender(),  # type: ignore[arg-type]
    )
    return support, canonical


def test_selected_encounter_bundle_carries_persisted_content_type() -> None:
    bundle = _bundle()

    assert bundle.encounter_id == "xalvakka"
    assert bundle.encounter_name == "Xalvakka"
    assert bundle.content_type == "trial"
    assert bundle.ready is True


def test_blank_role_content_type_inherits_selected_encounter_content_type() -> None:
    support, canonical = _support()
    role_evidence = _role_evidence()

    support.run(
        player_build=object(),  # type: ignore[arg-type]
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=_bundle(),
        role_evidence=role_evidence,
    )

    forwarded = canonical.calls[0]["role_evidence"]
    assert forwarded is not role_evidence
    assert forwarded.content_type == "trial"
    assert forwarded.reliable_group_healing is True
    assert role_evidence.content_type == ""


def test_explicit_role_content_type_is_not_overwritten_by_encounter_bundle() -> None:
    support, canonical = _support()
    role_evidence = _role_evidence(content_type="arena")

    support.run(
        player_build=object(),  # type: ignore[arg-type]
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=_bundle(),
        role_evidence=role_evidence,
    )

    assert canonical.calls[0]["role_evidence"] is role_evidence
    assert canonical.calls[0]["role_evidence"].content_type == "arena"


def test_absent_role_evidence_stays_absent_even_when_encounter_type_is_known() -> None:
    support, canonical = _support()

    support.run(
        player_build=object(),  # type: ignore[arg-type]
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=_bundle(),
    )

    assert canonical.calls[0]["role_evidence"] is None
