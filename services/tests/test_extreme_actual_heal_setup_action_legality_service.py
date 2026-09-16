from types import SimpleNamespace

from services.extreme_actual_heal_setup_action_legality_service import (
    GRANTS_RESOLVE,
    HAS_CAST_OR_CHANNEL_TIME,
    IS_ASSAULT_ABILITY,
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


class _TimingService:
    def __init__(self, rows: dict[str, object]) -> None:
        self.rows = rows
        self.calls: list[str] = []

    def resolve_skill(self, skill_id: str):
        self.calls.append(skill_id)
        evidence = self.rows.get(skill_id)
        return SimpleNamespace(evidence=evidence, unresolved=())


def _row(name: str, description: str, *, line: str = "Heavy Armor") -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line=line,
        skill_type="Active",
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=12340,
        max_rank=4,
        max_rank_ability_id=12345,
        description=description,
        domain=ExtremeSkillDomain.ARMOR,
    )


def _timing(*, cast: float | None, channel: float | None, channeled: bool = False):
    return SimpleNamespace(
        cast_time_seconds=cast,
        channel_time_seconds=channel,
        is_channeled=channeled,
    )


def _context() -> ExtremePlayerSkillLegalityContext:
    return ExtremePlayerSkillLegalityContext(equipped_class_lines=())


def test_setup_bridge_reuses_route_legal_nonultimate_candidate_service() -> None:
    provider = _StubCandidateService((
        _row("Resolve Witness", "Brace yourself, gaining Major Resolve for 20 seconds."),
    ))
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)
    result = service.witness(GRANTS_RESOLVE, _context())
    assert result.proven is True
    assert result.skill_name == "Resolve Witness"
    assert result.ability_id == 12345
    assert provider.calls == [(_context(), False)]


def test_setup_bridge_fails_closed_when_legal_candidates_do_not_prove_capability() -> None:
    provider = _StubCandidateService((_row("Irrelevant Skill", "Deal Flame Damage to an enemy."),))
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)
    result = service.witness(GRANTS_RESOLVE, _context())
    assert result.proven is False
    assert result.skill_name is None
    assert result.unresolved


def test_setup_bridge_does_not_treat_enemy_resolve_as_self_resolve() -> None:
    provider = _StubCandidateService((_row("Enemy Buff Example", "The enemy gains Major Resolve for 10 seconds."),))
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)
    result = service.witness(GRANTS_RESOLVE, _context())
    assert result.proven is False


def test_cast_time_capability_uses_canonical_timing_not_tooltip_text() -> None:
    row = _row("Cast Witness", "This tooltip says nothing about cast time.")
    provider = _StubCandidateService((row,))
    timing = _TimingService({"Cast Witness": _timing(cast=0.8, channel=0.0)})
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider, timing_service=timing)
    result = service.witness(HAS_CAST_OR_CHANNEL_TIME, _context())
    assert result.proven is True
    assert result.skill_name == "Cast Witness"
    assert "cast=0.8" in str(result.evidence)
    assert timing.calls


def test_channel_capability_accepts_positive_canonical_channel_time() -> None:
    row = _row("Channel Witness", "Channel some mysterious energy.")
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_StubCandidateService((row,)),
        timing_service=_TimingService({"Channel Witness": _timing(cast=0.0, channel=2.5, channeled=True)}),
    )
    result = service.witness(HAS_CAST_OR_CHANNEL_TIME, _context())
    assert result.proven is True
    assert result.skill_name == "Channel Witness"
    assert "channel=2.5" in str(result.evidence)


def test_instant_skill_does_not_satisfy_cast_or_channel_capability() -> None:
    row = _row("Instant Witness", "Instant ability.")
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_StubCandidateService((row,)),
        timing_service=_TimingService({"Instant Witness": _timing(cast=0.0, channel=0.0, channeled=False)}),
    )
    result = service.witness(HAS_CAST_OR_CHANNEL_TIME, _context())
    assert result.proven is False
    assert result.unresolved


def test_cast_or_channel_capability_fails_closed_without_timing_service() -> None:
    row = _row("Unknown Timing", "Perhaps lengthy. Perhaps not.")
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=_StubCandidateService((row,)))
    result = service.witness(HAS_CAST_OR_CHANNEL_TIME, _context())
    assert result.proven is False
    assert result.unresolved


def test_assault_capability_uses_route_legal_skill_line_identity() -> None:
    assault = _row("Vigor", "Heal yourself.", line="Assault")
    unrelated = _row("Other Skill", "Do something.", line="Heavy Armor")
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_StubCandidateService((unrelated, assault)),
    )
    result = service.witness(IS_ASSAULT_ABILITY, _context())
    assert result.proven is True
    assert result.skill_name == "Vigor"
    assert result.skill_line == "Assault"
    assert "Assault skill line" in str(result.evidence)


def test_unknown_setup_capability_fails_closed_without_querying_candidates() -> None:
    provider = _StubCandidateService(())
    service = ExtremeActualHealSetupActionLegalityService(candidate_service=provider)
    result = service.witness("invented_capability", _context())
    assert result.proven is False
    assert result.unresolved == ("unsupported H1 setup capability: invented_capability",)
    assert provider.calls == []
