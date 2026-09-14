from pathlib import Path


def test_shared_provider_workload_support_exposes_btv_calibration_on_both_pages():
    source = (
        Path(__file__).resolve().parents[1] / "team_provider_workload_support.py"
    ).read_text(encoding="utf-8")

    assert "BTVBenchmarkCorpus" in source
    assert "BTVBenchmarkEvidenceService.assess_temporal_result" in source
    assert "benchmark_assessments=_provider_btv_assessments(page, workloads)" in source
    assert "CompBuilderPage.set_provider_btv_benchmark_corpus" in source
    assert "OptimizationPage.set_provider_btv_benchmark_corpus" in source
    assert "CompBuilderPage.clear_provider_btv_benchmark_corpus" in source
    assert "OptimizationPage.clear_provider_btv_benchmark_corpus" in source


def test_btv_calibration_is_not_hardwired_to_every_provider_card():
    source = (
        Path(__file__).resolve().parents[1] / "team_provider_workload_support.py"
    ).read_text(encoding="utf-8")

    assert "page._provider_btv_benchmark_corpus = None" in source
    assert "if corpus is None:\n        return {}" in source
