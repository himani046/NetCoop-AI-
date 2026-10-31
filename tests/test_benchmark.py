"""Offline benchmark regression tests: deterministic and label-aware."""
from benchmark import make_dataset, classification_metrics, evaluate

def test_dataset_is_seeded_and_balanced():
    first=make_dataset(per_class=2,seed=17)
    assert first==make_dataset(per_class=2,seed=17)
    assert len(first)==12
    assert {row["expected"] for row in first} == {
        "normal","link_congestion","weak_wifi_signal",
        "physical_interface_fault","dhcp_failure","inconclusive"
    }

def test_confusion_and_scores():
    rows=[
        {"expected":"link_congestion","predicted":"link_congestion"},
        {"expected":"link_congestion","predicted":"inconclusive"},
        {"expected":"inconclusive","predicted":"inconclusive"},
    ]
    result=classification_metrics(rows)
    assert result["total"]==3
    assert result["accuracy"]==0.6667
    assert result["per_class"]["link_congestion"]["recall"]==0.5
    assert result["confusion"]["link_congestion"]["inconclusive"]==1

def test_end_to_end_offline_benchmark(monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL",raising=False)
    result=evaluate(make_dataset(per_class=1,seed=7))
    assert result["total"]==6
    assert result["ai_used"] is False
    assert result["accuracy"] >= 0
    assert len(result["rows"])==6
    assert set(result["per_class"]) >= {"normal","inconclusive"}
