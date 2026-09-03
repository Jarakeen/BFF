from minmax.build_candidate_comparison import ConstraintStatus
from minmax.build_candidate_evaluator import (
    _provider_scope_configuration_unresolved,
    _provider_scope_constraint,
)


def _resolver(_build):
    return ()


def test_provider_scope_is_explicitly_absent_when_neither_side_is_supplied() -> None:
    assert _provider_scope_configuration_unresolved(None, None) == ()
    assert _provider_scope_constraint(()) is None


def test_provider_scope_is_complete_when_baseline_and_resolver_are_supplied() -> None:
    assert _provider_scope_configuration_unresolved((), _resolver) == ()


def test_baseline_assignments_without_candidate_resolver_fail_closed() -> None:
    unresolved = _provider_scope_configuration_unresolved((), None)
    constraint = _provider_scope_constraint(unresolved)

    assert unresolved
    assert "must be supplied together" in unresolved[0]
    assert constraint is not None
    assert constraint.name == "provider responsibilities"
    assert constraint.status is ConstraintStatus.UNKNOWN
    assert "unresolved" in constraint.explanation.casefold()


def test_candidate_resolver_without_baseline_assignments_fails_closed() -> None:
    unresolved = _provider_scope_configuration_unresolved(None, _resolver)
    constraint = _provider_scope_constraint(unresolved)

    assert unresolved
    assert constraint is not None
    assert constraint.status is ConstraintStatus.UNKNOWN
