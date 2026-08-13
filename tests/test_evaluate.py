from pathlib import Path

from evaluate import evaluate


def test_labeled_sample_metrics():
    from build_sample import build

    source = Path("data/red_herring_prospectus.docx")
    if not source.exists():
        build()
    result, _ = evaluate(source, Path("output/redacted_prospectus.docx"))
    assert result["overall"]["precision"] == 1.0
    assert result["overall"]["recall"] == 1.0
    assert result["overall"]["accuracy"] == 1.0
    assert result["leftover_gold_in_output"] == []
    assert result["non_pii_lost"] == []
