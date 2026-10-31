"""Gemini agent behavior verified without external requests."""
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
import src.graph.workflow as workflow

def test_all_five_roles_have_reviews_without_mutating_diagnosis(monkeypatch):
    monkeypatch.setenv("NETCOOP_LLM_MODEL","gemini-2.5-flash")
    monkeypatch.setenv("NETCOOP_GEMINI_AGENT_REVIEWS","1")
    calls=[]
    def specialist(agent_id, telemetry, finding):
        calls.append(agent_id)
        return {"agent_id":agent_id,"explanation":"Observed measurements support the validated finding.",
                "evidence_metrics":[],"missing_measurements":[],"uncertainty":"Limited to one observation."}, None
    def correlate(telemetry, findings, deterministic_cause):
        calls.append("correlation_agent")
        return None,"Gemini second opinion not available"
    def reporting(report):
        calls.append("reporting_agent")
        return {"operator_summary":"Network incident assessment from validated evidence.",
                "explanation_of_actions":"Verify affected equipment before remediation.",
                "caveats":[]},None
    monkeypatch.setattr(workflow,"review_specialist",specialist)
    monkeypatch.setattr(workflow,"structured_second_opinion",correlate)
    monkeypatch.setattr(workflow,"review_report",reporting)
    state=diagnose(scenarios()["link_congestion"],"GEMINI-TEST")
    assert set(calls)=={"performance_agent","infrastructure_agent",
        "connectivity_agent","correlation_agent","reporting_agent"}
    assert len(state["gemini_agent_reviews"])==3
    assert state["gemini_report_review"]["operator_summary"]
    assert state["final_report"]["suspected_root_cause"]=="link_congestion"

def test_gemini_review_failures_do_not_stop_diagnosis(monkeypatch):
    monkeypatch.setenv("NETCOOP_LLM_MODEL","gemini-2.5-flash")
    monkeypatch.setattr(workflow,"review_specialist",
                        lambda *args:(None,"Gemini specialist review unavailable"))
    monkeypatch.setattr(workflow,"structured_second_opinion",
                        lambda *args:(None,"Gemini correlation unavailable"))
    monkeypatch.setattr(workflow,"review_report",
                        lambda *args:(None,"Gemini reporting unavailable"))
    state=diagnose(scenarios()["interface_fault"],"GEMINI-FAIL")
    assert state["final_report"]["suspected_root_cause"]=="physical_interface_fault"
    assert len(state["gemini_agent_reviews"])==3
    assert state["gemini_report_review"] is None

def test_gemini_offline_mode(monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL",raising=False)
    state=diagnose(scenarios()["link_congestion"],"GEMINI-OFFLINE")
    assert not state.get("gemini_agent_reviews")
    assert state["final_report"]["suspected_root_cause"]=="link_congestion"
