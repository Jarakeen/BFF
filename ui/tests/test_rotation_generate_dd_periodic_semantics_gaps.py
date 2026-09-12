from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.canonical_knowledge_gap import CanonicalKnowledgeDomain
from services.rotation_dd_periodic_runtime_semantics_gap_audit_service import (
    RotationDDPeriodicRuntimeSemanticsGap,
)
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _StaticContext:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="parse-cat-id")

    def maximum_amount_for(self, bar, resource):
        assert bar == "front"
        assert resource is ResourceType.MAGICKA
        return 30000


class _StaticContextService:
    def resolve(self, build):
        return _StaticContext()


class _Policies:
    def policies_for(self, encounter_id):
        return ()

    def threshold_policies_for(self, encounter_id):
        return ()

    def review_blockers_for(self, encounter_id):
        return ()


class _AuditService:
    def __init__(self, audit):
        self.audit = audit
        self.calls = []

    def audit_build(self, build):
        self.calls.append(build)
        return self.audit


class _Page:
    def __init__(self, build):
        self.build = build

    def _selected_build(self):
        return self.build

    def selected_encounter_id(self):
        return "test_encounter"

    def canonical_recovery_policy(self):
        return {
            "resource": ResourceType.MAGICKA,
            "trigger_fraction": 0.35,
        }

    def canonical_dd_evaluation_policy(self):
        return {"target_resistance": 18200.0}


def _provider(audit_service):
    return RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        demand_policy_provider=_Policies(),  # type: ignore[arg-type]
        dd_periodic_semantics_gap_audit_service=audit_service,  # type: ignore[arg-type]
    )


def test_dd_generate_context_surfaces_missing_periodic_semantics_as_advisory_gap() -> None:
    build = PlayerBuild(
        Name="Parse Cat",
        BuildName="DD",
        Role="DD",
        FrontBarSkills=["Wall of Elements", "", "", "", "", ""],
    )
    audit = SimpleNamespace(
        missing=(
            RotationDDPeriodicRuntimeSemanticsGap(
                skill_entity_id="wall_of_elements",
                skill_rank_id=101,
                coefficient_number=1,
                classification_source="verified runtime classification",
            ),
        ),
        unresolved=(),
    )
    audit_service = _AuditService(audit)

    context = _provider(audit_service).context_for(_Page(build))

    assert audit_service.calls == [build]
    gaps = context.evidence_inputs.knowledge_gaps
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.domain is CanonicalKnowledgeDomain.SKILL_MECHANIC
    assert gap.key == "wall_of_elements.coefficient_1.periodic_runtime_semantics"
    assert "wall_of_elements coefficient 1" in gap.summary
    assert gap.blocking is False


def test_non_dd_generate_context_does_not_run_periodic_semantics_audit() -> None:
    build = PlayerBuild(Name="Healer", BuildName="Heal", Role="Healer")
    audit_service = _AuditService(SimpleNamespace(missing=(), unresolved=()))

    context = _provider(audit_service).context_for(_Page(build))

    assert audit_service.calls == []
    assert context.evidence_inputs.knowledge_gaps == ()


def test_dd_unresolved_periodic_identity_surfaces_as_advisory_research_gap() -> None:
    build = PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DPS")
    audit_service = _AuditService(
        SimpleNamespace(
            missing=(),
            unresolved=("mystery_skill: coefficient 2 damage periodic identity is unresolved",),
        )
    )

    context = _provider(audit_service).context_for(_Page(build))

    assert len(context.evidence_inputs.knowledge_gaps) == 1
    gap = context.evidence_inputs.knowledge_gaps[0]
    assert gap.domain is CanonicalKnowledgeDomain.SKILL_MECHANIC
    assert "mystery_skill" in gap.summary
    assert gap.blocking is False
