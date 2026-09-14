from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
from ui.rotation_generate_tank_role_evidence_support import (
    RotationGenerateTankObligationContext,
    RotationGenerateTankRoleEvidenceSupport,
)


class _Build:
    Role = "Tank"


class _HardFactory:
    def __call__(self, database_path, **kwargs):
        return SimpleNamespace(database_path=database_path, **kwargs)


class _PlanFactory:
    def __call__(self, **kwargs):
        return SimpleNamespace(**kwargs)


class _SlotService:
    def __init__(self, *, unresolved=()):
        self.unresolved = tuple(unresolved)
        self.calls = []
        self.slot_requirement = object()

    def resolve(self, build):
        self.calls.append(build)
        return SimpleNamespace(
            slot_requirements=(self.slot_requirement,),
            unresolved=self.unresolved,
        )


class _ProjectorFactory:
    def __init__(self):
        self.calls = []
        self.projector = SimpleNamespace(active=True)

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.projector


def _bundle():
    return RotationCanonicalEvidenceBundle(
        encounter_id="taleria_hm",
        encounter_name="Taleria",
        demands=(),
        options=(),
        requirements=(),
        passives=(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.25,
        content_type="trial",
    )


def _context():
    return RotationGenerateTankObligationContext(
        encounter_id="taleria_hm",
        defensive_obligations=(object(),),
        defensive_claims=(object(),),
    )


def test_tank_generate_attaches_explicit_strategy_projector_to_plan_evidence():
    context = _context()
    slots = _SlotService()
    projector_factory = _ProjectorFactory()
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=_HardFactory(),
        plan_evidence_factory=_PlanFactory(),
        family_projector_factory=projector_factory,
        action_slot_service=slots,
    )

    result = support.compose(player_build=_Build(), evidence_bundle=_bundle())

    assert slots.calls == [result.plan_evidence_provider.build]
    assert result.plan_evidence_provider.candidate_projector is projector_factory.projector
    assert len(projector_factory.calls) == 1
    call = projector_factory.calls[0]
    assert call["defensive_obligations"] == context.defensive_obligations
    assert call["defensive_claims"] == context.defensive_claims
    assert call["slot_requirements"] == (slots.slot_requirement,)
    assert call["taunt_application_claims"] == ()
    assert call["taunt_maintenance_policies"] == ()


def test_tank_generate_obligations_without_strategy_do_not_create_projector():
    context = RotationGenerateTankObligationContext(
        encounter_id="taleria_hm",
        defensive_obligations=(object(),),
    )
    slots = _SlotService()
    projector_factory = _ProjectorFactory()
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=_HardFactory(),
        plan_evidence_factory=_PlanFactory(),
        family_projector_factory=projector_factory,
        action_slot_service=slots,
    )

    result = support.compose(player_build=_Build(), evidence_bundle=_bundle())

    assert slots.calls == []
    assert projector_factory.calls == []
    assert not hasattr(result.plan_evidence_provider, "candidate_projector")


def test_tank_generate_strategy_fails_closed_on_unresolved_saved_build_slot_identity():
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: _context(),
        database_path="eso.db",
        hard_obligation_factory=_HardFactory(),
        plan_evidence_factory=_PlanFactory(),
        family_projector_factory=_ProjectorFactory(),
        action_slot_service=_SlotService(unresolved=("Pierce Armor ambiguous",)),
    )

    with pytest.raises(ValueError, match="slot identity is unresolved"):
        support.compose(player_build=_Build(), evidence_bundle=_bundle())
