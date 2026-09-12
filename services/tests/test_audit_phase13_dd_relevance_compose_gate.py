from dataclasses import dataclass

from tools.audit_phase13_dd_whole_plan_damage_coverage import _DDAuditStaticContextService


@dataclass(frozen=True)
class _Progression:
    resolved: bool = True


@dataclass(frozen=True)
class _Result:
    progression: _Progression
    unresolved: tuple[str, ...]
    contexts: tuple[object, ...] = (object(),)

    @property
    def resolved(self) -> bool:
        return self.progression.resolved and bool(self.contexts) and not self.unresolved


class _Delegate:
    def __init__(self, unresolved: tuple[str, ...]) -> None:
        self.unresolved = unresolved
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return _Result(
            progression=_Progression(),
            unresolved=self.unresolved,
        )


def test_audit_compose_adapter_removes_only_dd_ambient_diagnostics() -> None:
    delegate = _Delegate(
        (
            "front static context: Champion Point effect not yet modeled: Master Gatherer: harvest",
            "front static context: Champion Point effect not yet modeled: Celerity: movement",
            "front static context: Potion selected; activation/uptime is not part of static build state: Alliance Battle Draught",
            "front static context: Passive rank is not recorded for character: Last Gasp",
            "back static context: Passive rank is not recorded for character: Health Avarice",
        )
    )
    service = _DDAuditStaticContextService(delegate)  # type: ignore[arg-type]

    result = service.resolve("build", combat_state="state")

    assert result.resolved is True
    assert result.unresolved == ()
    assert delegate.calls == [("build", {"combat_state": "state"})]


def test_audit_compose_adapter_keeps_unknown_offensive_gap_blocking() -> None:
    service = _DDAuditStaticContextService(
        _Delegate(("front static context: Mystery offensive modifier is unresolved",))  # type: ignore[arg-type]
    )

    result = service.resolve("build")

    assert result.resolved is False
    assert result.unresolved == (
        "front static context: Mystery offensive modifier is unresolved",
    )
