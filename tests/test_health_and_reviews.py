"""Healthy classification and Gemini validation regression tests."""
from unittest.mock import MagicMock
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
from src.agents.gemini_review import review_specialist
import src.agents.gemini_review as gemini
import src.graph.workflow as workflow

def test_complete_normal_snapshot_is_healthy(monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL", raising=False)
    state = diagnose(scenarios()["normal_operation"], "INC-HEALTHY")
    report = state["final_report"]
    assert report["status"] == "healthy"
    assert report["suspected_root_cause"] == "No network fault detected"
    assert report["confidence"] == 0
    assert report["alternative_causes"] == []
    assert report["recommended_actions"] == ["Continue routine network monitoring"]
    assert len(report["evidence_sources"]) == 3

def test_incomplete_normal_snapshot_stays_inconclusive(monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL", raising=False)
    report = diagnose({"device_id":"SW1", "latency_ms":12, "packet_loss_pct":0})["final_report"]
    assert report["status"] == "inconclusive"

def test_ai_alternatives_cannot_pollute_report(monkeypatch):
    monkeypatch.setenv("NETCOOP_LLM_MODEL", "gemini-3.1-flash-lite")
    monkeypatch.setenv("NETCOOP_GEMINI_AGENT_REVIEWS", "0")
    from src.agents.llm_fallback import SecondOpinion
    monkeypatch.setattr(workflow, "structured_second_opinion",
        lambda *args: (SecondOpinion(suggested_cause=None,
            explanation="No abnormalities observed in the measured network telemetry.",
            requires_more_data=False,
            alternative_causes=["Unsubstantiated speculative outage"],
            evidence_metrics=["latency_ms"]), None))
    state = diagnose(scenarios()["normal_operation"])
    assert state["final_report"]["status"] == "healthy"
    assert state["final_report"]["alternative_causes"] == []
    assert state["decision"]["ai_review"]["alternative_causes"]

def test_specialist_review_accepts_missing_identity_and_validates_metric_names(monkeypatch):
    monkeypatch.setenv("NETCOOP_LLM_MODEL", "gemini-3.1-flash-lite")
    monkeypatch.setenv("NETCOOP_GEMINI_AGENT_REVIEWS", "1")
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema): return self
        def invoke(self, messages):
            return {"explanation":"All observed latency and link metrics appear within normal thresholds.",
                    "evidence_metrics":["latency_ms"],"missing_measurements":[],
                    "uncertainty":"A single telemetry snapshot has limited predictive value."}
    import langchain_google_genai
    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeModel)
    review, warning = review_specialist("performance_agent", {"latency_ms":24}, {})
    assert warning is None
    assert review["agent_id"] == "performance_agent"
    assert review["evidence_metrics"] == ["latency_ms"]

def test_gemini_metric_citations_with_values_are_normalized():
    from src.agents.gemini_review import verified_metric_names
    observed = {"cpu_pct": 23, "latency_ms": 24.0, "packet_loss_pct": 0}
    assert verified_metric_names(
        ["cpu_pct: 23.0", "latency_ms: 24.0", "packet_loss_pct: 0.0"],
        observed,
    ) == ["cpu_pct", "latency_ms", "packet_loss_pct"]

def test_gemini_metric_citation_rejects_invented_values():
    import pytest
    from src.agents.gemini_review import verified_metric_names
    with pytest.raises(ValueError, match="incorrect cited value"):
        verified_metric_names(["cpu_pct: 99.0"], {"cpu_pct": 23})
    with pytest.raises(ValueError, match="unknown cited metric"):
        verified_metric_names(["nonexistent_metric: 10"], {"cpu_pct": 23})

def test_complete_colab_healthy_telemetry_with_metadata_warnings(monkeypatch):
    """Generator omits site/parent_id and supplies an external status label."""
    monkeypatch.delenv("NETCOOP_LLM_MODEL", raising=False)
    payload = {
        "timestamp": "2026-10-31T19:12:30.188633Z",
        "device_id": "HOSTEL_SW_01",
        "status": "Healthy",
        "metrics": {
            "cpu_utilization_pct": 19.98, "memory_pct": 34.46,
            "link_utilization_pct": 32.04, "packet_loss_pct": 0,
            "latency_ms": 13.37, "jitter_ms": 4.32,
            "queue_drops": 0, "crc_errors": 0, "rssi_dbm": -52.61,
            "snr_db": 35.94, "retransmissions_pct": 2.69,
            "dhcp_timeout_pct": 0, "dns_latency_ms": 42.14,
            "gateway_ping_ms": 3.16, "throughput_mbps": 69.07,
        },
    }
    state=diagnose(payload)
    assert state["final_report"]["status"] == "healthy"
    assert state["final_report"]["suspected_root_cause"] == "No network fault detected"
    assert state["final_report"]["confidence"] == 0
    assert any("Missing site" in w for w in state["warnings"])
    assert any("Input status" in w for w in state["warnings"])


def test_numeric_data_quality_warning_prevents_false_healthy(monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL", raising=False)
    from src.utils.synthetic_data import scenarios
    payload = dict(scenarios()["normal_operation"])
    payload["unexpected_measurement"] = 99
    state = diagnose(payload)
    assert state["final_report"]["status"] == "inconclusive"
