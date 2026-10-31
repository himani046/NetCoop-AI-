"""Mocked AI tests: no paid API calls, no network or credentials required."""
from src.agents.llm_fallback import SecondOpinion
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
import src.graph.workflow as workflow

def test_ai_advisory_retains_authoritative_cause(monkeypatch):
    monkeypatch.setenv("NETCOOP_LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("NETCOOP_GEMINI_AGENT_REVIEWS", "0")
    def mock_review(telemetry, findings, deterministic_cause):
        assert deterministic_cause == "link_congestion"
        return SecondOpinion(
            suggested_cause="device_overload",
            explanation="CPU may contribute to symptoms, but congestion evidence remains primary.",
            requires_more_data=True,
            alternative_causes=["device_overload"],
            evidence_metrics=["cpu_pct", "link_utilization_pct"]), None
    monkeypatch.setattr(workflow, "structured_second_opinion", mock_review)
    state=diagnose(scenarios()["link_congestion"],"INC-AI-TEST")
    report=state["final_report"]
    assert report["suspected_root_cause"] == "link_congestion"
    assert state["decision"]["ai_review"]["suggested_cause"] == "device_overload"
    assert any("no automatic override" in note for note in state["resolution_notes"])

def test_ai_failure_is_nonfatal(monkeypatch):
    monkeypatch.setenv("NETCOOP_LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("NETCOOP_GEMINI_AGENT_REVIEWS", "0")
    monkeypatch.setattr(workflow, "structured_second_opinion",
                        lambda *args: (None, "AI unavailable; deterministic diagnosis retained"))
    state=diagnose(scenarios()["interface_fault"],"INC-AI-FAILURE")
    assert state["final_report"]["suspected_root_cause"] == "physical_interface_fault"
    assert "ai_review" not in state["final_report"]
    assert any("AI unavailable" in note for note in state["resolution_notes"])

def test_disabled_ai_has_no_ai_review(monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL",raising=False)
    state=diagnose(scenarios()["link_congestion"],"INC-OFFLINE")
    assert state["final_report"]["status"] == "diagnosed"
    assert "ai_review" not in state["final_report"]
