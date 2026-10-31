"""Regression coverage for organizer-style Colab incident payloads."""
import json
from pathlib import Path
from src.protocol.normalizer import normalize
from src.graph.workflow import diagnose

DATA = Path(__file__).resolve().parents[1] / "data"

def test_uploaded_flat_colab_sample():
    payload = json.loads((DATA / "colab_sample.json").read_text())
    state = diagnose(payload, "INC-COLAB-FLAT")
    assert state["normalized_telemetry"]["cpu_pct"] == 99.9
    assert state["final_report"]["status"] == "diagnosed"
    assert state["final_report"]["suspected_root_cause"] == "link_congestion"

def test_original_nested_generator_sample():
    payload = json.loads((DATA / "colab_original_nested.json").read_text())
    state = diagnose(payload, "INC-COLAB-NESTED")
    normalized = state["normalized_telemetry"]
    assert normalized["cpu_pct"] == 99.9
    assert normalized["link_utilization_pct"] == 100
    assert normalized["interface_errors"] == 160
    assert state["final_report"]["suspected_root_cause"] == "link_congestion"
    assert any("not necessarily CRC" in w for w in state["warnings"])

def test_malformed_metrics_object_does_not_crash():
    normalized, warnings = normalize({"device_id":"A","metrics": "invalid"})
    assert normalized["latency_ms"] is None
    assert any("metrics must be" in w for w in warnings)

def test_top_level_value_overrides_nested_metric():
    normalized, warnings = normalize({"device_id":"A","metrics":{"latency_ms":280},"latency_ms":20})
    assert normalized["latency_ms"] == 20
