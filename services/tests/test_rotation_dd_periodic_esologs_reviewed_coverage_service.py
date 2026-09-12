from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_reviewed_coverage_service import (
    RotationDDPeriodicEsoLogsReviewedCoverageService,
)


class _ReviewEntry:
    def __init__(
        self,
        skill_entity_id,
        *,
        executable_complete=False,
        unresolved_executable_fields=(),
    ):
        self.skill_entity_id = skill_entity_id
        self.executable_complete = executable_complete
        self.unresolved_executable_fields = tuple(unresolved_executable_fields)


class _ReviewService:
    def load(self):
        return (
            _ReviewEntry(
                "meteor",
                unresolved_executable_fields=(
                    "activation_anchor",
                    "first_tick_offset_seconds",
                    "refresh_boundary",
                    "magnitude_policy",
                ),
            ),
            _ReviewEntry("stampede", executable_complete=True),
            _ReviewEntry(
                "stampede",
                unresolved_executable_fields=("magnitude_policy",),
            ),
            _ReviewEntry(
                "scalding_rune",
                unresolved_executable_fields=("reviewed_interval_seconds", "activation_anchor"),
            ),
        )


class _DiscoveryService:
    def __init__(self):
        self.calls = []

    def inspect_skill(self, skill_entity_id):
        self.calls.append(skill_entity_id)
        reports = {
            "meteor": SimpleNamespace(
                cast_count=0,
                candidates=(),
                unresolved=("meteor: no matching ESO Logs cast observations found",),
            ),
            "stampede": SimpleNamespace(
                cast_count=12,
                candidates=(object(), object()),
                unresolved=(),
            ),
            "scalding_rune": SimpleNamespace(
                cast_count=3,
                candidates=(object(),),
                unresolved=("scalding_rune: weak candidate evidence",),
            ),
        }
        return reports[skill_entity_id]


def test_reports_observed_reviewed_skills_first_and_composes_existing_discovery() -> None:
    discovery = _DiscoveryService()
    report = RotationDDPeriodicEsoLogsReviewedCoverageService(
        canonical_database_path="unused.db",
        logs_database_path="unused-logs.db",
        review_service=_ReviewService(),
        discovery_service=discovery,
    ).inspect()

    assert discovery.calls == ["meteor", "stampede", "scalding_rune"]
    assert tuple(row.skill_entity_id for row in report.rows) == (
        "stampede",
        "scalding_rune",
        "meteor",
    )
    assert tuple(row.skill_entity_id for row in report.observed_rows) == (
        "stampede",
        "scalding_rune",
    )

    stampede = report.rows[0]
    assert stampede.component_count == 2
    assert stampede.cast_count == 12
    assert stampede.candidate_count == 2
    assert stampede.executable_component_count == 1
    assert stampede.unresolved_executable_fields == ("magnitude_policy",)
    assert stampede.evidence_unresolved == ()

    meteor = report.rows[-1]
    assert meteor.observed is False
    assert meteor.cast_count == 0
    assert meteor.evidence_unresolved == (
        "meteor: no matching ESO Logs cast observations found",
    )
