from services.extreme_actual_heal_setup_action_legality_service import (
    GRANTS_RESOLVE,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


class _StubCandidateService:
    def __init__(self, rows: tuple[ExtremePlayerSkillRecord, ...]) -> None:
        self.rows = rows
        self.calls: list[tuple[ExtremePlayerSkillLegalityContext, bool | None]] = []

    def candidates(self, context, *, ultimate=None):
        self.calls.append((context, ultimate))
        return self.rows


def _row(name: str, description: str, *, line: str = "Heavy Armor") -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line=line,
        skill_type="Active",
        description=description,
        domain=ExtremeSkillDomain.ARMOR,
        is_passive=False,
        is_player=True,
        max_rank_ability_id=12345,
        base_ability_id=12340,
        is_crafted=False,
        known_noncombat_line=False,
        combat_line=True,
    )


def _context() -> ExtremePlayerSkillLegalityContext:
    return ExtremePlayerSkillLegalityContext(equipped_class_lines=())


def test_setup_bridge_reuses_route_legal_nonultimate_candidate_service() -> None:
    provider = _StubCandidateService(
        (
            _row(
                "Resolve Witness",
                "Brace yourself, gaining Major Resolve for 20 seconds.",
            ),
        )
    )
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)

    result = service.witness(GRANTS_RESOLVE, _context())

    assert result.proven is True
    assert result.skill_name == "Resolve Witness"
    assert result.ability_id == 12345
    assert provider.calls == [(_context(), False)]


def test_setup_bridge_fails_closed_when_legal_candidates_do_not_prove_capability() -> None:
    provider = _StubCandidateService(
        (
            _row("Irrelevant Skill", "Deal Flame Damage to an enemy."),
        )
    )
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)

    result = service.witness(GRANTS_RESOLVE, _context())

    assert result.proven is False
    assert result.skill_name is None
    assert result.unresolved


def test_setup_bridge_does_not_treat_enemy_resolve_as_self_resolve() -> None:
    provider = _StubCandidateService(
        (
            _row(
                "Enemy Buff Example",
                "The enemy gains Major Resolve for 10 seconds.",
            ),
        )
    )
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)

    result = service.witness(GRANTS_RESOLVE, _context())

    assert result.proven is False


def test_unknown_setup_capability_fails_closed_without_querying_candidates() -> None:
    provider = _StubCandidateService(())
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)

    result = service.witness("invented_capability", _context())

    assert result.proven is False
    assert result.unresolved == ("unsupported H1 setup capability: invented_capability",)
    assert provider.calls == []
