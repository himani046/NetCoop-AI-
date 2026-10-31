"""Interoperability, replay rejection, and arbitration checks."""
from src.protocol.validator import validate_messages
from src.protocol.models import AgentEnvelope, AgentFinding
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios

def valid_message():
    finding=AgentFinding(agent_id="performance_agent",status="HEALTHY",
                         confidence_contribution=0)
    return AgentEnvelope(correlation_id="INC-1",sender="performance_agent",
                         recipient="correlation_agent",payload=finding).model_dump(mode="json")

def test_valid_acp():
    accepted, warnings=validate_messages([valid_message()],"INC-1")
    assert len(accepted)==1
    assert not any("Rejected" in warning for warning in warnings)

def test_wrong_schema_and_correlation():
    for key,value in (("schema_version","0.1.0"),("correlation_id","OTHER")):
        message=valid_message()
        message[key]=value
        accepted,warnings=validate_messages([message],"INC-1")
        assert not accepted
        assert any("Rejected" in warning for warning in warnings)

def test_misrouted_or_impersonated():
    for kind in ("recipient","sender"):
        message=valid_message()
        if kind=="recipient":
            message["recipient"]="reporting_agent"
        else:
            message["payload"]["agent_id"]="other_agent"
        accepted,warnings=validate_messages([message],"INC-1")
        assert not accepted
        assert any("Rejected" in warning for warning in warnings)

def test_duplicate_replay():
    m=valid_message()
    accepted,warnings=validate_messages([m,m],"INC-1")
    assert len(accepted)==1
    assert any("Duplicate" in warning for warning in warnings)

def test_graph_uses_validated_specialists():
    state=diagnose(scenarios()["link_congestion"],"INC-ACP")
    assert len(state["validated_messages"])==3
    assert state["final_report"]["suspected_root_cause"]=="link_congestion"

def test_conflict_arbitration_trace():
    telemetry=scenarios()["link_congestion"] | {"crc_errors":15000,"link_utilization_pct":14}
    state=diagnose(telemetry,"INC-CONFLICT")
    assert state["final_report"]["suspected_root_cause"]=="physical_interface_fault"
    assert any(m.get("message_type")=="arbitration" for m in state["messages"])
