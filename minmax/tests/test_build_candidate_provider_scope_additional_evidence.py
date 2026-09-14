from types import SimpleNamespace

from minmax.build_candidate_provider_scope import BuildCandidateProviderScope
from models.build_model import PlayerBuild
from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    RosterCapabilityEvidence,
)
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _audit(build: PlayerBuild) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=build.Name,
        build_name=build.BuildName,
        character_id=build.Name,
        resolved_sources=(),
        resolved_effects=(),
        conditional_sources=(),
        unresolved=(),
        capability_unresolved=(),
        boundaries=(),
    )


class _CapabilityService:
    def audit_build(self, build):
        return _audit(build)


class _Evaluator:
    def __init__(self):
        self.additional = []

    def evaluate_saved_build_audits(self, encounter_id, audits, *, additional_capability_evidence=()):
        self.additional.append(tuple(additional_capability_evidence))
        return SimpleNamespace(snapshot=tuple(audit.build_name for audit in audits))


class _Candidates:
    def candidates(self, report, audits):
        return (report.snapshot,)


class _Assignments:
    def assign(self, rows):
        return tuple(rows)


def _build(name, build_name, skills=()):
    build = PlayerBuild(Name=name, BuildName=build_name)
    build.FrontBarSkills = list(skills)
    return build


def test_provider_scope_recomputes_additional_capability_evidence_for_candidate_build():
    evaluator = _Evaluator()

    def resolver(builds):
        return tuple(
            RosterCapabilityEvidence(
                member_id=build.Name,
                capability_type="taunt",
                assessment=(
                    CapabilityAssessment.SUPPORTED
                    if "Pierce Armor" in build.FrontBarSkills
                    else CapabilityAssessment.UNSUPPORTED
                ),
                source=build.BuildName,
            )
            for build in builds
        )

    tank = _build("tank-a", "Tank Base", ())
    healer = _build("healer-a", "Healer", ())
    scope = BuildCandidateProviderScope.create(
        encounter_id="xalvakka",
        member_id="tank-a",
        roster_builds=(tank, healer),
        capability_service=_CapabilityService(),
        roster_evaluator=evaluator,
        candidate_service=_Candidates(),
        assignment_service=_Assignments(),
        additional_capability_evidence_resolver=resolver,
    )

    assert evaluator.additional[0][0].assessment is CapabilityAssessment.UNSUPPORTED

    scope.assignments_for(_build("tank-a", "Tank Candidate", ("Pierce Armor",)))

    assert evaluator.additional[-1][0].assessment is CapabilityAssessment.SUPPORTED
    assert evaluator.additional[-1][0].source == "Tank Candidate"
    assert evaluator.additional[-1][1].source == "Healer"
