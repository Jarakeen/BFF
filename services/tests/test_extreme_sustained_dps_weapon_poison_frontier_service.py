from types import SimpleNamespace

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonFrontierService,
)


def _formula(name):
    return AlchemyFormula(
        reagents=(f"{name} A", f"{name} B"),
        traits=(name,),
        game_update=GameUpdate.U50,
    )


class _Repository:
    def __init__(self, formulas=(), unresolved=()):
        self._catalog = SimpleNamespace(
            formulas=tuple(formulas),
            unresolved=tuple(unresolved),
        )

    def catalog(self):
        return self._catalog


def test_two_bar_poison_frontier_is_ordered_cartesian_product() -> None:
    service = ExtremeSustainedDPSWeaponPoisonFrontierService(
        _Repository((_formula("Breach"), _formula("Protection")))
    )

    result = service.frontier()

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert len(result.selections) == 3
    assert result.candidate_count == 9
    assert result.selections[0].is_none is True


def test_one_bar_poison_frontier_does_not_search_irrelevant_back_bar() -> None:
    service = ExtremeSustainedDPSWeaponPoisonFrontierService(
        _Repository((_formula("Breach"), _formula("Protection")))
    )

    result = service.frontier(one_bar_only=True)

    assert result.denominator_proven is True
    assert result.one_bar_only is True
    assert result.candidate_count == 3


def test_candidate_materializes_only_front_and_back_poison_state() -> None:
    breach = _formula("Breach")
    protection = _formula("Protection")
    service = ExtremeSustainedDPSWeaponPoisonFrontierService(
        _Repository((breach, protection))
    )
    baseline = PlayerBuild(
        Name="Generated",
        BuildName="Candidate",
        Role="DD",
        Potion="Keep Potion",
        FrontBarPoison="Old Front",
        BackBarPoison="Old Back",
    )

    candidate = service.candidate_at(
        baseline,
        index=5,
    )

    assert candidate.front.formula == breach
    assert candidate.back.formula == protection
    assert candidate.build.FrontBarPoison == breach.canonical_id
    assert candidate.build.BackBarPoison == protection.canonical_id
    assert candidate.build.Potion == "Keep Potion"
    assert candidate.build.Name == "Generated"


def test_one_bar_candidate_forces_back_poison_empty() -> None:
    breach = _formula("Breach")
    service = ExtremeSustainedDPSWeaponPoisonFrontierService(
        _Repository((breach,))
    )
    baseline = PlayerBuild(
        Name="Generated",
        BuildName="Candidate",
        Role="DD",
        BackBarPoison="Must Not Survive",
    )

    candidate = service.candidate_at(
        baseline,
        index=1,
        one_bar_only=True,
    )

    assert candidate.front.formula == breach
    assert candidate.build.BackBarPoison == ""
    assert candidate.back.is_none is True


def test_poison_frontier_fails_closed_on_catalog_debt() -> None:
    service = ExtremeSustainedDPSWeaponPoisonFrontierService(
        _Repository((_formula("Breach"),), unresolved=("source conflict",))
    )

    result = service.frontier()

    assert result.denominator_proven is False
    assert "source conflict" in result.unresolved


def test_poison_frontier_requires_at_least_one_canonical_formula() -> None:
    result = ExtremeSustainedDPSWeaponPoisonFrontierService(
        _Repository()
    ).frontier()

    assert result.denominator_proven is False
    assert result.candidate_count == 1
    assert any(
        "has no selectable formulas" in row
        for row in result.unresolved
    )
