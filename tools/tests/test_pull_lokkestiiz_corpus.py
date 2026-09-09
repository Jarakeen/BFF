from __future__ import annotations

from tools.pull_lokkestiiz_corpus import (
    DEFAULT_DSR_CONTROL_REPORT,
    DEFAULT_SUNSPIRE_REPORTS,
    pull_corpus,
)


class FakeClient:
    def __init__(self) -> None:
        self.fights_by_report = {
            "AAA": [
                {"id": 1, "name": "Yolnahkriin", "startTime": 0, "endTime": 1000},
                {"id": 2, "name": "Lokkestiiz", "startTime": 1000, "endTime": 3000},
                {"id": 3, "name": "Nahviintaas", "startTime": 3000, "endTime": 5000},
            ]
        }

    def get_fights(self, report_code: str):
        return self.fights_by_report.get(report_code, [])

    def _query(self, query: str, variables: dict):
        return {"reportData": {"report": {"playerDetails": {"data": {"playerDetails": {}}}}}}


def test_defaults_keep_sunspire_reports_separate_from_dsr_control() -> None:
    assert len(DEFAULT_SUNSPIRE_REPORTS) == 4
    assert DEFAULT_DSR_CONTROL_REPORT not in DEFAULT_SUNSPIRE_REPORTS


def test_corpus_filters_full_sunspire_report_to_lokkestiiz_only(monkeypatch) -> None:
    monkeypatch.setattr(
        "tools.pull_lokkestiiz_corpus.fetch_all_events",
        lambda client, code, fight_id, start, end, include_resources, limit: [
            {"type": "damage", "timestamp": start + 100}
        ],
    )

    corpus = pull_corpus(client=FakeClient(), report_codes=("AAA",))
    report = corpus["reports"]["AAA"]

    assert report["matching_fight_count"] == 1
    assert tuple(report["fights"]) == ("2",)
    assert report["fights"]["2"]["metadata"]["name"] == "Lokkestiiz"
    assert report["fights"]["2"]["event_count"] == 1
