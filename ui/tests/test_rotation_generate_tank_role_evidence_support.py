from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from services.rotation_tank_defensive_obligation_service import RotationTankDefensiveObligation
from minmax.rotation_plan import RotationActionKind
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
from ui.rotation_generate_tank_role_evidence_support import (
    RotationGenerateTankObligationContext,
    RotationGenerateTankRoleEvidenceSupport,
    install_rotation_generate_tank_obligation_context,
)


class _Build:
    Role = "Tank"


class _HardFactory:
    def __init__(self):
        self.calls = []

    def __call__(self, database_path, **kwargs):
        result = SimpleNamespace(database_path=database_path, **kwargs)
        self.calls.append(result)
        return result


class _PlanFactory:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        result = SimpleNamespace(**kwargs)
        self.calls.append(result)
        return result


def _bundle(encounter_id="taleria_hm"):
    return RotationCanonicalEvidenceBundle(
        encounter_id=encounter_id,
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


def _defensive():
    return RotationTankDefensiveObligation(
        obligation_id="heavy",
        window_start_seconds=10.0,
        window_end_seconds=11.0,
        allowed_actions=(RotationActionKind.BLOCK,),
    )


def test_tank_generate_composes_canonical_hard_obligation_provider():
    hard = _HardFactory()
    plan = _PlanFactory()
    context = RotationGenerateTankObligationContext(
        encounter_id="taleria_hm",
        defensive_obligations=(_defensive(),),
    )
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=hard,
        plan_evidence_factory=plan,
    )

    result = support.compose(player_build=_Build(), evidence_bundle=_bundle())

    assert result.role_key == "tank"
    assert result.content_type == "trial"
    assert len(hard.calls) == 1
    assert hard.calls[0].defensive_obligations == (_defensive(),)
    assert plan.calls[0]["role_hard_obligation_evidence_provider"] is hard.calls[0]
    assert plan.calls[0]["resource"] is ResourceType.MAGICKA


def test_tank_generate_fails_closed_without_explicit_obligation_context():
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: None,
        database_path="eso.db",
        plan_evidence_factory=_PlanFactory(),
        hard_obligation_factory=_HardFactory(),
    )

    with pytest.raises(ValueError, match="no explicit encounter-scoped Tank obligation context"):
        support.compose(player_build=_Build(), evidence_bundle=_bundle())


def test_tank_generate_rejects_stale_context_for_other_encounter():
    context = RotationGenerateTankObligationContext(
        encounter_id="xalvakka_hm",
        defensive_obligations=(_defensive(),),
    )
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        plan_evidence_factory=_PlanFactory(),
        hard_obligation_factory=_HardFactory(),
    )

    with pytest.raises(ValueError, match="does not match selected encounter"):
        support.compose(player_build=_Build(), evidence_bundle=_bundle("taleria_hm"))


def test_tank_generate_rejects_empty_context_instead_of_auto_passing():
    context = RotationGenerateTankObligationContext(encounter_id="taleria_hm")
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        plan_evidence_factory=_PlanFactory(),
        hard_obligation_factory=_HardFactory(),
    )

    with pytest.raises(ValueError, match="contains no explicit obligations"):
        support.compose(player_build=_Build(), evidence_bundle=_bundle())


def test_tank_generate_requires_tank_saved_build_role():
    context = RotationGenerateTankObligationContext(
        encounter_id="taleria_hm",
        defensive_obligations=(_defensive(),),
    )
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        plan_evidence_factory=_PlanFactory(),
        hard_obligation_factory=_HardFactory(),
    )

    with pytest.raises(ValueError, match="explicit Tank saved-build role"):
        support.compose(player_build=SimpleNamespace(Role="Healer"), evidence_bundle=_bundle())


def test_page_context_install_exposes_explicit_setter_and_getter():
    page = SimpleNamespace()
    install_rotation_generate_tank_obligation_context(page)
    context = RotationGenerateTankObligationContext(
        encounter_id="taleria_hm",
        defensive_obligations=(_defensive(),),
    )

    assert page.rotation_generate_tank_obligation_context() is None
    page.set_rotation_generate_tank_obligation_context(context)
    assert page.rotation_generate_tank_obligation_context() is context
    page.set_rotation_generate_tank_obligation_context(None)
    assert page.rotation_generate_tank_obligation_context() is None
