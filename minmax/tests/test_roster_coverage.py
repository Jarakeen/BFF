from minmax.roster_capability_resolver import RosterCapabilityProvider
from minmax.roster_coverage import RosterCoverageAnalyzer
from minmax.role import Role
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _effect(
    name: str,
    *,
    magnitude: float = 10,
    target_type: SupportTargetType = SupportTargetType.GROUP,
    target_count: int | None = None,
    range: float | None = None,
) -> SupportEffect:
    return SupportEffect(
        source="Test Source",
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type=name,
        target_type=target_type,
        magnitude=magnitude,
        target_count=target_count,
        range=range,
    )


def test_coverage_creates_one_entry_per_capability():
    capabilities = {
        "major_courage": (
            RosterCapabilityProvider(
                character_name="Healer",
                role=Role.HEALER,
                effect=_effect("major_courage"),
            ),
        ),
        "major_slayer": (
            RosterCapabilityProvider(
                character_name="Tank",
                role=Role.TANK,
                effect=_effect("major_slayer"),
            ),
        ),
    }

    report = RosterCoverageAnalyzer().analyze(capabilities)

    assert report.effect_names() == (
        "major_courage",
        "major_slayer",
    )

    assert len(report.all()) == 2


def test_coverage_preserves_all_providers():
    capabilities = {
        "major_courage": (
            RosterCapabilityProvider(
                character_name="Healer One",
                role=Role.HEALER,
                effect=_effect("major_courage", magnitude=430),
            ),
            RosterCapabilityProvider(
                character_name="Tank One",
                role=Role.TANK,
                effect=_effect("major_courage", magnitude=300),
            ),
        ),
    }

    report = RosterCoverageAnalyzer().analyze(capabilities)

    entry = report.for_effect("major_courage")

    assert entry is not None
    assert len(entry.providers) == 2

    assert {
        provider.character_name
        for provider in entry.providers
    } == {
        "Healer One",
        "Tank One",
    }

    assert [
        provider.effect.magnitude
        for provider in entry.providers
    ] == [430, 300]


def test_coverage_preserves_mechanical_constraints():
    capabilities = {
        "major_slayer": (
            RosterCapabilityProvider(
                character_name="Healer",
                role=Role.HEALER,
                effect=_effect(
                    "major_slayer",
                    magnitude=10,
                    target_count=5,
                    range=28,
                ),
            ),
        ),
    }

    report = RosterCoverageAnalyzer().analyze(capabilities)

    entry = report.for_effect("major_slayer")

    assert entry is not None
    assert len(entry.providers) == 1

    effect = entry.providers[0].effect

    assert effect.magnitude == 10
    assert effect.target_type == SupportTargetType.GROUP
    assert effect.target_count == 5
    assert effect.range == 28


def test_missing_capability_returns_none():
    report = RosterCoverageAnalyzer().analyze({})

    assert report.for_effect("major_slayer") is None
    assert report.effect_names() == ()