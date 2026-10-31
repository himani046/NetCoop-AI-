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
