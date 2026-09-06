from __future__ import annotations


_INSTALLED = False
_ORIGINAL_CHAIR_CANDIDATES = None


def _chair_candidates_with_final_constraints(page, row: int):
    """Apply hard chair constraints after every candidate source has contributed.

    Trial routing and ESO Logs snapshot injection both wrap the candidate service.
    This final guard deliberately installs after those wrappers so saved builds,
    reference templates, and live snapshots all traverse the same class/gear gate.
    """

    assert _ORIGINAL_CHAIR_CANDIDATES is not None
    candidates = tuple(_ORIGINAL_CHAIR_CANDIDATES(page, row))

    from ui import comp_builder_build_constraint_support as constraint_support

    constraint = constraint_support._constraint_for_row(page, row)
    if constraint is None:
        return candidates
    return tuple(
        candidate
        for candidate in candidates
        if constraint_support.candidate_matches_constraint(candidate, constraint)
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_CHAIR_CANDIDATES
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as candidate_support

    _ORIGINAL_CHAIR_CANDIDATES = candidate_support._chair_candidates
    candidate_support._chair_candidates = _chair_candidates_with_final_constraints
    _INSTALLED = True
